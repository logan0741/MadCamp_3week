import socket
import threading
import sys

TARGET_HOST = '::1'
TARGET_PORT = 8000
LISTEN_PORT = 8001

def handle(client_socket):
    print(f"Handling connection from {client_socket.getpeername()}", flush=True)
    try:
        remote_socket = socket.create_connection((TARGET_HOST, TARGET_PORT))
        print(f"Connected to backend {TARGET_HOST}:{TARGET_PORT}", flush=True)
    except Exception as e:
        print(f"Failed to connect to target: {e}")
        client_socket.close()
        return

    def forward(src, dst):
        try:
            while True:
                data = src.recv(4096)
                if not data: break
                dst.sendall(data)
        except:
            pass
        finally:
            try:
                src.close()
            except:
                pass
            try:
                dst.close()
            except:
                pass

    threading.Thread(target=forward, args=(client_socket, remote_socket), daemon=True).start()
    threading.Thread(target=forward, args=(remote_socket, client_socket), daemon=True).start()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(('0.0.0.0', LISTEN_PORT))
    except Exception as e:
        print(f"Failed to bind: {e}")
        sys.exit(1)
        
    server.listen(5)
    print(f"Proxy listening on {LISTEN_PORT} -> {TARGET_HOST}:{TARGET_PORT}")

    while True:
        try:
            client, addr = server.accept()
            print(f"Accepted connection from {addr}")
            threading.Thread(target=handle, args=(client,), daemon=True).start()
        except Exception as e:
            print(f"Accept error: {e}")

if __name__ == '__main__':
    main()
