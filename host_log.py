import socket
import threading

HOST = 'localhost'
PORT = 6000
clave_secreta = 'clave123'

log = []
autenticados = set()
clientes = {}  # Mapa de nombre a socket
lock = threading.Lock()

def manejar_cliente(conn, addr):
    global log, autenticados
    nombre = conn.recv(1024).decode()
    with lock:
        clientes[nombre] = conn
    print(f"[Host Log] {nombre} conectado desde {addr}")

    while True:
        try:
            datos = conn.recv(1024).decode()
            if not datos:
                break
            partes = datos.split('|')
            comando = partes[0]

            if comando == 'AUTHENTICATE':
                clave_recibida = partes[1]
                if clave_recibida == clave_secreta:
                    with lock:
                        autenticados.add(nombre)
                    conn.sendall('AUTHSUCCESS'.encode())
                    print(f"[Host Log] {nombre} autenticado correctamente.")
                else:
                    conn.sendall('AUTHFAIL'.encode())
                    print(f"[Host Log] {nombre} falló la autenticación.")

            elif comando == 'ADD_LOG':
                if nombre in autenticados:
                    mensaje = partes[1]
                    with lock:
                        log.append(f"{nombre}: {mensaje}")
                        autenticados.remove(nombre)  # Autenticación válida solo para un mensaje
                    conn.sendall('LOGADDED'.encode())
                    print(f"[Host Log] Mensaje añadido al log: {mensaje}")
                    broadcast_new_log_state()
                else:
                    conn.sendall('NOTAUTHENTICATED'.encode())
                    print(f"[Host Log] {nombre} intentó añadir al log sin autenticarse.")

        except Exception as e:
            print(f"[Host Log] Error al manejar el cliente {nombre}: {e}")
            break

    conn.close()
    with lock:
        if nombre in clientes:
            del clientes[nombre]
        if nombre in autenticados:
            autenticados.remove(nombre)
    print(f"[Host Log] {nombre} desconectado.")

def broadcast_new_log_state():
    global log
    with lock:
        estado_log = '|'.join(log)
        for cliente in clientes.values():
            try:
                cliente.sendall(f"NEW_LOG_STATE|{estado_log}".encode())
            except:
                print("[Host Log] Error al enviar el estado del log a un cliente.")

with socket.socket() as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"[Host Log] Esperando conexiones en {HOST}:{PORT}...")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()
