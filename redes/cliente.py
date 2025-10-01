# cliente.py
import socket
import json
import time
import os

MAX_DATAGRAM_SIZE = 65507 
TIMEOUT = 5               
MAX_RETRIES = 3           

def udp_request(peer_address, command: str):
    server_host, server_port = peer_address.split(':')
    server_addr = (server_host, int(server_port))
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
        client_socket.settimeout(TIMEOUT)
        request_message = f"{command}|".encode('utf-8')
        for attempt in range(MAX_RETRIES):
            try:
                client_socket.sendto(request_message, server_addr)
                response_data, _ = client_socket.recvfrom(MAX_DATAGRAM_SIZE)
                response_message = response_data.decode('utf-8')
                res_parts = response_message.split('|', 1)
                return res_parts[0], json.loads(res_parts[1]) if len(res_parts) > 1 else {}
            except socket.timeout:
                continue
    raise TimeoutError(f"Nenhuma resposta de {peer_address}")

def udp_get_file_content(peer_address, filename: str) -> bytes:
    server_host, server_port = peer_address.split(':')
    server_addr = (server_host, int(server_port))
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as file_socket:
        file_socket.settimeout(TIMEOUT)
        request_message = f"FILE_REQ|{filename}".encode('utf-8')
        
        chunks = {}
        total_chunks = -1

        for attempt in range(MAX_RETRIES):
            try:
                file_socket.sendto(request_message, server_addr)
                while True:
                    packet, source_addr = file_socket.recvfrom(MAX_DATAGRAM_SIZE)
                    if source_addr[0] != server_addr[0]: continue
                    
                    parts = packet.split(b'|', 3)
                    command = parts[0].decode('utf-8')
                    
                    if command == "FILE_CHUNK":
                        seq, total, data_chunk = int(parts[1]), int(parts[2]), parts[3]
                        if total_chunks == -1: total_chunks = total
                        if seq not in chunks: chunks[seq] = data_chunk
                        
                        ack_message = f"ACK|{seq}".encode('utf-8')
                        file_socket.sendto(ack_message, source_addr)

                        if len(chunks) == total_chunks:
                            return b"".join(chunks[i] for i in sorted(chunks.keys()))
                    elif command == "FILE_ERR":
                        raise ConnectionAbortedError(f"Erro no servidor: {parts[1].decode('utf-8')}")
            except socket.timeout:
                continue
        raise TimeoutError(f"Falha no download de {filename} após {MAX_RETRIES} tentativas.")

def sync_loop(state):
    while True:
        try:
            state.scan_and_update_meta()
            print(f"\n[{state.node_id}] Iniciando ciclo de sincronização...")

            for peer in state.peers:
                try:
                    res_cmd, idx = udp_request(peer, "INDEX_REQ")
                    if res_cmd != "INDEX_RSP": continue

                    rfiles = idx.get("files", {})
                    for name, info in rfiles.items():
                        r_mtime, r_hash = int(info.get("mtime", 0)), info.get("sha256")
                        
                        if state.need_download(name, r_mtime, r_hash, peer):
                            print(f"[{state.node_id}] ⬇️  Baixando: {name} de {peer}...")
                            try:
                                data = udp_get_file_content(peer, name)
                                state.save_downloaded_file(name, data, r_mtime)
                                print(f"[{state.node_id}] ✅ Arquivo {name} baixado e salvo com sucesso.")
                            except Exception as e:
                                print(f"[{state.node_id}] ❌ ERRO no download de {name}: {e}")
                except Exception as e:
                    print(f"[{state.node_id}] Falha ao sincronizar com peer {peer}: {e}")
            
        except Exception as e:
            print(f"[{state.node_id}] ERRO geral no sync loop: {e}")
            
        time.sleep(state.sync_interval)