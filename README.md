# Sistema de Sincronização de Arquivos P2P via UDP

## Descrição

Este projeto é uma implementação de um sistema de sincronização de arquivos peer-to-peer (P2P) desenvolvido para a disciplina de Redes de Computadores. A aplicação permite que múltiplos nós (peers) em uma rede mantenham um diretório de arquivos sincronizado em tempo real.

Toda a comunicação é realizada sobre o protocolo **UDP**, o que exigiu a criação de uma camada de controle para garantir a entrega confiável de dados, simulando funcionalidades encontradas em protocolos como o TCP. O sistema é projetado para ser resiliente, detectando e replicando criações, modificações e exclusões de arquivos entre os nós da rede.

## Passo a passo para execução
-Python3
## Para execução local 
* Abra 4 Terminais: Você usará 3 para os nós e 1 como "Terminal de Controle".
* Navegue até a Pasta Raiz: Em todos os quatro terminais, execute o comando cd para entrar na pasta do seu projeto.
* Limpe Dados Antigos: No Terminal de Controle, execute o comando abaixo para apagar a pasta sync_data de testes anteriores.
* Crie as Pastas de Sincronização: No Terminal de Controle, crie a estrutura de diretórios limpa.
   * mkdir sync_data/nodo1
   * mkdir sync_data/nodo2
   * mkdir sync_data/nodo3
*-Execute um comando em cada um dos três terminais reservados para os nós.
  * No Terminal 1:
      * python3 main.py --config config_local/nodo1.json
  * No Terminal 2:
      * python3 main.py --config config_local/nodo2.json
  * No Terminal 3:
      * python3 main.py --config config_local/nodo3.json
* Use o Terminal de controle para realizar os testes:
   * Cirar Arquivo:
        *echo "teste local" > sync_data/nodo1/local.txt
    *Deletar Arquivo:
        * del sync_data/nodo3/local.txt

## Para execução com Docker
* Inicie o Docker Desktop: Garanta que o aplicativo esteja aberto e o motor em execução.
* Abra 1 Terminal: Você só precisa de um terminal principal para o Docker Compose.
* Navegue até a Pasta Raiz: Execute o cd para entrar na pasta do projeto.
* Construa e Inicie os Containers: No terminal principal, execute:
    * docker compose up --build
* No segundo terminal, crie:
       * echo "teste com docker" > sync_data/nodo1/docker.txt
* Deletar: Repita os mesmos testes de modificação e exclusão da execução local. O comportamento será o mesmo.


## Funcionalidades Principais

-   **Rede P2P Estática:** A topologia da rede é definida por arquivos de configuração, onde cada nó conhece os outros peers.
-   **Sincronização Automática:** Os nós verificam periodicamente o estado dos outros peers e iniciam a sincronização quando detectam diferenças.
-   **Detecção de Mudanças por Metadados:** As alterações são detectadas comparando metadados dos arquivos, incluindo **data de modificação** e **hash SHA256**, garantindo precisão e eficiência.
-   **Protocolo de Transferência Confiável sobre UDP:**
    -   **Segmentação:** Arquivos são divididos em pequenos pacotes (`chunks`) para transmissão.
    -   **Confirmação e Retransmissão:** Cada `chunk` enviado exige uma confirmação (`ACK`) do receptor. Se o `ACK` não chegar dentro de um tempo limite (timeout), o `chunk` é reenviado.
-   **Suporte a Múltiplos Ambientes:** O sistema pode ser executado e testado tanto em ambiente **local** (localhost) quanto em um ambiente de **containers com Docker**, simulando uma rede real.

