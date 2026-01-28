#!/bin/sh
set -e

echo "==================================================="
echo "MemeForty Reverse SSH Tunnel"
echo "==================================================="
echo "Target: ${SSH_USER}@${SSH_HOST}:${SSH_PORT}"
echo "Tunnels:"
echo "  - Frontend  :3000 -> VPS :3000"
echo "  - Backend   :8000 -> VPS :8000"
echo "  - AI Engine :8001 -> VPS :8001"
echo "  - Static    :8080 -> VPS :8080"
echo "==================================================="

# Check SSH key permissions
# Check SSH key permissions
if [ -f /root/.ssh/id_rsa ]; then
    cp /root/.ssh/id_rsa /root/.ssh/id_rsa_temp
    chmod 600 /root/.ssh/id_rsa_temp
    echo "SSH key found and permissions set (using copy)."
else
    echo "ERROR: SSH key not found at /root/.ssh/id_rsa"
    echo "Please mount your SSH key using:"
    echo "  volumes:"
    echo "    - ~/.ssh/id_rsa:/root/.ssh/id_rsa:ro"
    exit 1
fi

# Wait for services to be ready
echo "Waiting for internal services to start..."
sleep 10

# Test connectivity to SSH host
echo "Testing connectivity to ${SSH_HOST}..."
if ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes \
    -i /root/.ssh/id_rsa_temp -p ${SSH_PORT} ${SSH_USER}@${SSH_HOST} exit 2>/dev/null; then
    echo "WARNING: Cannot connect to ${SSH_HOST}. Will retry with autossh..."
fi

echo "Starting autossh tunnel..."

# Start autossh with reverse tunnels
# -M 0: Disable autossh's own monitoring (use ServerAlive instead)
# -N: Don't execute remote command
# -R: Reverse tunnel (remote port -> local service)
exec autossh -M 0 -N \
    -o "ServerAliveInterval=30" \
    -o "ServerAliveCountMax=3" \
    -o "StrictHostKeyChecking=no" \
    -o "ExitOnForwardFailure=yes" \
    -o "TCPKeepAlive=yes" \
    -o "ConnectTimeout=30" \
    -R 3000:frontend:3000 \
    -R 8000:backend:8000 \
    -R 80:nginx:80 \
    -R 8001:ai-engine:8001 \
    -R 8080:nginx-static:8080 \
    -i /root/.ssh/id_rsa_temp \
    -p ${SSH_PORT} \
    ${SSH_USER}@${SSH_HOST}
