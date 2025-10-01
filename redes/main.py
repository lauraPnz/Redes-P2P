# main.py
import argparse
import time # Importar time
from utilidades import read_json
from status_node import NodeState
from servidor import UDPServer 
from cliente import sync_loop 
import threading

def main():
    parser = argparse.ArgumentParser(description="P2P File Sync (UDP)")
    parser.add_argument("--config", required=True, help="Caminho para o arquivo de configuração")
    args = parser.parse_args()

    cfg = read_json(args.config, None)
    if not cfg:
        raise SystemExit("Erro ao ler arquivo de configuração.")

    state = NodeState(cfg)
    
    server_thread = UDPServer(state) 
    client_thread = threading.Thread(target=sync_loop, args=(state,), daemon=True)

    # Inicia PRIMEIRO o servidor para que ele possa receber conexões
    server_thread.start()
    
    # <<< CORREÇÃO DEFINITIVA PARA O ConnectionResetError >>>
    # Dá uma pequena pausa para garantir que os servidores de todos os peers 
    # estejam no ar antes que os clientes comecem a enviar mensagens.
    print("Aguardando 2 segundos para a rede estabilizar...")
    time.sleep(2)

    # Inicia o cliente, que começará a procurar outros peers
    client_thread.start()

    print(f"[OK] Nó {state.node_id} (Porta UDP: {state.port}) iniciado. Diretório: {state.directory}")
    print(f"Pressione Ctrl+C para encerrar.")
    
    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("\nEncerrando...")
        server_thread.stop()

if __name__ == "__main__":
    main()