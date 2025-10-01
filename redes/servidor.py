# servidor.py
import socket
import threading
import json
import os
import math
from status_node import NodeState 

MAX_DATAGRAM_SIZE = 65507 
CHUNK_SIZE = 1400      
TIMEOUT = 5
MAX_RETRIES = 3           

class UDPServer(threading.Thread):
    def __init__(self, state: NodeState):
        super().__init__()
        self.state = state
        self.host = '0.0.0.0'
        self.port = state.port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.bind((self.host, self.port))
        self.running = True
        print(f"[Servidor UDP] Escutando em {self.host}:{self.port}")

    def run(self):
        while self.running:
            try:
                data, address = self.server_socket.recvfrom(MAX_DATAGRAM_SIZE)
                if not data.startswith(b'ACK|'):
                    threading.Thread(target=self.handle_request, args=(data, address)).start()
            except Exception as e:
                if self.running: print(f"[Erro Servidor UDP] {e}")

    def handle_request(self, data, address):
        try:
            message = data.decode('utf-8', errors='ignore')
            parts = message.split('|', 1)
            command, payload = parts[0], parts[1] if len(parts) > 1 else ""

            if command == "INDEX_REQ":
                self._send_index(address)
            elif command == "FILE_REQ":
                self._start_file_transfer(address, payload)
        except Exception as e:
            print(f"Erro ao processar requisição de {address}: {e}")

    def _send_response(self, address, response_type: str, data):
        message = f"{response_type}|{json.dumps(data)}".encode('utf-8')
        self.server_socket.sendto(message, address)

    def _send_index(self, address):
        payload = self.state.index_payload()
        self._send_response(address, "INDEX_RSP", payload)
        
    def _start_file_transfer(self, client_address, filename):
        file_path = os.path.join(self.state.directory, filename)
        
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as transfer_socket:
            transfer_socket.settimeout(TIMEOUT)
            if not os.path.exists(file_path):
                transfer_socket.sendto(b"FILE_ERR|NotFound", client_address)
                return

            with open(file_path, "rb") as f: file_data = f.read()
            
            chunks = [file_data[i:i + CHUNK_SIZE] for i in range(0, len(file_data), CHUNK_SIZE)] if file_data else [b'']
            total_chunks = len(chunks)

            for seq, chunk_data in enumerate(chunks):
                header = f"FILE_CHUNK|{seq}|{total_chunks}|".encode('utf-8')
                message = header + chunk_data
                ack_received = False
                for attempt in range(MAX_RETRIES):
                    try:
                        transfer_socket.sendto(message, client_address)
                        ack_data, addr = transfer_socket.recvfrom(1024)
                        if addr == client_address and ack_data.decode('utf-8') == f"ACK|{seq}":
                            ack_received = True
                            break
                    except socket.timeout:
                        continue
                if not ack_received:
                    raise TimeoutError(f"Falha ao receber ACK para o chunk {seq}")
            print(f"[{self.state.node_id}] Transferência de '{filename}' concluída para {client_address}")

    def stop(self):
        print("Parando o servidor UDP...")
        self.running = False
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM).sendto(b'', (self.host, self.port))
        self.server_socket.close()