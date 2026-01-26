FROM alpine:3.18

# Install autossh and openssh-client
RUN apk add --no-cache autossh openssh-client curl

# Create SSH directory
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Environment variables with defaults
ENV SSH_HOST=voice-anime-fight.p-e.kr
ENV SSH_USER=root
ENV SSH_PORT=22
ENV AUTOSSH_GATETIME=0
ENV AUTOSSH_POLL=30

ENTRYPOINT ["/entrypoint.sh"]
