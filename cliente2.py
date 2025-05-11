import socket
import threading

HOST = 'localhost'
PORT = 5000

nombre = input("Ingresa tu nombre (ej: P2): ")

def escuchar(sock):
    while True:
        data = sock.recv(1024).decode()
        if data == 'OK':
            print("[Cliente] Permiso concedido, autenticando...")
            clave = input("Ingresa la clave secreta: ")
            sock.sendall(f'AUTHENTICATE|{clave}'.encode())
        elif data == 'AUTHSUCCESS':
            mensaje = input("Autenticado. Ingresa el mensaje a escribir en el log: ")
            sock.sendall(f'APPEND|{mensaje}'.encode())
        elif data == 'AUTHFAIL':
            print("[Cliente] Clave incorrecta. Abortando intento.")
        elif data == 'CONFIRMACION':
            print("[Cliente] Mensaje agregado al log correctamente.")

def main():
    with socket.socket() as s:
        s.connect((HOST, PORT))
        s.sendall(nombre.encode())
        threading.Thread(target=escuchar, args=(s,), daemon=True).start()

        while True:
            entrada = input("\nPresiona Enter para solicitar acceso al log...")
            s.sendall('REQUEST'.encode())

if __name__ == "__main__":
    main()
