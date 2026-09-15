#!/usr/bin/env python3
"""
Simple HTTP/HTTPS Web Proxy Server
"""

import socket
import threading
import sys
from urllib.parse import urlparse

class WebProxy:
    def __init__(self, host='127.0.0.1', port=8888):
        self.host = host
        self.port = port
        self.server_socket = None
        self.buffer_size = 4096

    def start(self):
        """Start the proxy server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        
        print(f"[*] Web Proxy started on {self.host}:{self.port}")
        print(f"[*] Set your browser proxy to {self.host}:{self.port}")
        
        try:
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"[+] Client connected: {client_address}")
                
                # Handle client in a new thread
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.daemon = True
                client_thread.start()
        except KeyboardInterrupt:
            print("\n[!] Shutting down proxy...")
            self.server_socket.close()
            sys.exit(0)

    def handle_client(self, client_socket, client_address):
        """Handle individual client connections"""
        try:
            # Receive request from client
            request = client_socket.recv(self.buffer_size).decode('utf-8', errors='ignore')
            
            if not request:
                client_socket.close()
                return
            
            print(f"[*] Request from {client_address}:")
            print(request.split('\r\n')[0])
            
            # Parse the request
            request_line = request.split('\r\n')[0]
            method, url, protocol = request_line.split(' ')
            
            # Handle CONNECT (HTTPS)
            if method == 'CONNECT':
                self.handle_connect(client_socket, url)
            else:
                # Handle HTTP requests
                self.handle_http(client_socket, request, url)
        
        except Exception as e:
            print(f"[!] Error handling client: {e}")
        finally:
            client_socket.close()

    def handle_http(self, client_socket, request, url):
        """Handle HTTP requests"""
        try:
            # Parse URL
            parsed_url = urlparse(url if url.startswith('http') else f'http://{url}')
            host = parsed_url.hostname
            port = parsed_url.port or 80
            path = parsed_url.path or '/'
            if parsed_url.query:
                path += f'?{parsed_url.query}'
            
            # Connect to remote server
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            
            # Modify request to remove absolute URL
            modified_request = request.replace(url, path, 1)
            remote_socket.sendall(modified_request.encode('utf-8'))
            
            # Forward response back to client
            while True:
                data = remote_socket.recv(self.buffer_size)
                if not data:
                    break
                client_socket.sendall(data)
            
            remote_socket.close()
        except Exception as e:
            print(f"[!] HTTP error: {e}")
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")

    def handle_connect(self, client_socket, url):
        """Handle HTTPS CONNECT tunneling"""
        try:
            # Parse host and port
            host, port = url.split(':')
            port = int(port)
            
            # Send success response
            client_socket.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            
            # Connect to remote server
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((host, port))
            
            # Create bidirectional tunnel
            self.tunnel(client_socket, remote_socket)
            
            remote_socket.close()
        except Exception as e:
            print(f"[!] CONNECT error: {e}")
            client_socket.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")

    def tunnel(self, client_socket, remote_socket):
        """Create a bidirectional tunnel between client and remote server"""
        def forward(src, dst):
            while True:
                try:
                    data = src.recv(self.buffer_size)
                    if not data:
                        break
                    dst.sendall(data)
                except:
                    break
        
        # Create threads for bidirectional forwarding
        thread1 = threading.Thread(target=forward, args=(client_socket, remote_socket))
        thread2 = threading.Thread(target=forward, args=(remote_socket, client_socket))
        
        thread1.daemon = True
        thread2.daemon = True
        
        thread1.start()
        thread2.start()
        
        # Wait for threads to complete
        thread1.join()
        thread2.join()


if __name__ == '__main__':
    proxy = WebProxy()
    proxy.start()
