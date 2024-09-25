import sys
import socket
import threading

def server_loop(local_host, local_port, remote_host, remote_port, receive_first):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server.bind((local_host, local_port))
    except Exception as e:
        print(f"[*] Erro ao ligar o servidor no {local_host}:{local_port} - {e}")
        sys.exit(0)

    print(f"[*] Escutando no {local_host}:{local_port}")

    server.listen(5)

    while True:
        client_socket, addr = server.accept()

        print(f"[*] Conexão recebida de {addr[0]}:{addr[1]}")

        # Iniciar uma thread para lidar com o proxy
        proxy_thread = threading.Thread(target=proxy_handler, args=(client_socket, remote_host, remote_port, receive_first))
        proxy_thread.start()

def proxy_handler(client_socket, remote_host, remote_port, receive_first):
    # Conectar ao servidor remoto
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    remote_socket.connect((remote_host, remote_port))

    # Receber dados do servidor remoto primeiro, se necessário
    if receive_first:
        remote_buffer = receive_from(remote_socket)
        if len(remote_buffer):
            print(f"[*] Recebido {len(remote_buffer)} bytes do servidor remoto")
            hexdump(remote_buffer)

            # Enviar para o cliente local
            client_socket.send(remote_buffer)

    # Loop para manejar a comunicação entre cliente e servidor
    while True:
        # Receber dados do cliente local
        local_buffer = receive_from(client_socket)

        if len(local_buffer):
            print(f"[*] Recebido {len(local_buffer)} bytes do cliente")
            hexdump(local_buffer)

            # Aqui você pode modificar os dados enviados pelo cliente se quiser
            remote_socket.send(local_buffer)
            print("[*] Enviado para o servidor remoto")

        # Receber a resposta do servidor remoto
        remote_buffer = receive_from(remote_socket)

        if len(remote_buffer):
            print(f"[*] Recebido {len(remote_buffer)} bytes do servidor remoto")
            hexdump(remote_buffer)

            # Aqui você pode modificar os dados recebidos do servidor
            client_socket.send(remote_buffer)
            print("[*] Enviado de volta para o cliente")

        # Se não houver mais dados de qualquer lado, encerrar as conexões
        if not len(local_buffer) or not len(remote_buffer):
            client_socket.close()
            remote_socket.close()
            print("[*] Conexões encerradas")
            break

def hexdump(src, length=16):
    result = []
    digits = 4 if isinstance(src, str) else 2

    for i in range(0, len(src), length):
        s = src[i:i+length]
        hexa = ' '.join([f"{x:0{digits}X}" for x in s])
        text = ''.join([chr(x) if 0x20 <= x < 0x7F else '.' for x in s])
        result.append(f"{i:04X}   {hexa:<{length*(digits+1)}}   {text}")

    print("\n".join(result))

def receive_from(connection):
    buffer = b""
    connection.settimeout(2)

    try:
        while True:
            data = connection.recv(4096)
            if not data:
                break
            buffer += data
    except:
        pass

    return buffer

def main():
    # Argumentos de exemplo para proxy
    if len(sys.argv[1:]) != 5:
        print("Uso: ./proxy.py [localhost] [localport] [remotehost] [remoteport] [receive_first]")
        print("Exemplo: ./proxy.py 127.0.0.1 9000 10.12.132.1 9000 True")
        sys.exit(0)

    # Configurações locais
    local_host = sys.argv[1]
    local_port = int(sys.argv[2])

    # Configurações do host remoto
    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])

    # Este argumento determina se devemos primeiro receber dados do servidor
    receive_first = sys.argv[5] == "True"

    # Iniciar o loop do servidor proxy
    server_loop(local_host, local_port, remote_host, remote_port, receive_first)

if __name__ == "__main__":
    main()

