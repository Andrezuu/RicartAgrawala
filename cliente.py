import socket

HOST = 'localhost'
PORT = 5000

nombre = input("Ingresa tu nombre (ej: P1): ")
with socket.socket() as s:
    s.connect((HOST, PORT))
    s.sendall(nombre.encode())  # Enviar nombre al servidor
    started = False
    while True:
        if not started:
            input("\nPresiona Enter para solicitar acceso al log...")
            s.sendall('REQUEST'.encode())  # Enviar REQUEST al servidor
            started = True

        # Esperar respuesta del servidor
        respuesta = s.recv(1024).decode()
        print(f"[Cliente] Mensaje recibido: {respuesta}")

        if respuesta == 'OK':
            print("[Cliente] Permiso concedido, autenticando...")
            clave = input("Ingresa la clave secreta: ")
            s.sendall(f'AUTHENTICATE|{clave}'.encode())

        elif respuesta == 'AUTHSUCCESS':
            mensaje = input("Autenticado. Ingresa el mensaje a escribir en el log: ")
            s.sendall(f'APPEND|{mensaje}'.encode())
        elif respuesta == 'CONFIRMACION':
            print("[Cliente] Mensaje agregado al log correctamente.")
            started = False
        elif respuesta == 'AUTHFAIL':
            print("[Cliente] Clave incorrecta. Abortando intento.")
            started = False
        elif respuesta == 'COLA':
            print("[Cliente] Permiso denegado. Estás en la cola de espera.")
            started = False

