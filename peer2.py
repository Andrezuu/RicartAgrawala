
import socket
import threading
import time

HOST = 'localhost'
PORT = 6002
clave_secreta = 'clave123'

# Estados de Ricart & Agrawala
RELEASED = 0
WANTED = 1
HELD = 2

# Variables globales
estado = RELEASED
reloj = 0
replies_pendientes = 0
cola_RA = []
lock = threading.Lock()
log_local = []
peers = []  # Lista de direcciones de otros peers

def actualizar_reloj(otro_reloj):
    global reloj
    with lock:
        reloj = max(reloj, otro_reloj) + 1

def manejar_conexiones():
    """Hilo para manejar conexiones entrantes de otros peers."""
    with socket.socket() as server_socket:
        server_socket.bind((HOST, PORT))
        server_socket.listen()
        print(f"[{nombre}] Esperando conexiones en {HOST}:{PORT}...")

        while True:
            conn, addr = server_socket.accept()
            threading.Thread(target=manejar_mensaje, args=(conn, addr), daemon=True).start()

def manejar_mensaje(conn, addr):
    """Maneja mensajes entrantes de otros peers."""
    global estado, reloj, cola_RA, replies_pendientes
    with conn:
        datos = conn.recv(1024).decode()
        if not datos:
            return
        partes = datos.split('|')
        comando = partes[0]

        if comando == 'REQUEST':
            timestamp = (int(partes[1]), partes[2])
            peer = partes[2]
            with lock:
                reloj = max(reloj, timestamp[0]) + 1
                if estado == HELD or (estado == WANTED and (timestamp < (reloj, nombre))):
                    cola_RA.append((timestamp, peer))
                else:
                    enviar_reply(peer)

        elif comando == 'REPLY':
            with lock:
                replies_pendientes -= 1

def enviar_reply(peer):
    """Envía un mensaje REPLY a otro peer."""
    for p in peers:
        if p[0] == peer:
            with socket.socket() as s:
                s.connect((p[1], p[2]))
                s.sendall(f"REPLY|{nombre}".encode())
            break

def multicast_request(timestamp, nombre):
    """Envía un mensaje REQUEST a todos los peers."""
    for peer in peers:
        with socket.socket() as s:
            s.connect((peer[1], peer[2]))
            s.sendall(f"REQUEST|{timestamp[0]}|{nombre}".encode())

def solicitar_acceso(nombre):
    """Solicita acceso al recurso crítico."""
    global estado, reloj, replies_pendientes
    with lock:
        reloj += 1
        estado = WANTED
        timestamp = (reloj, nombre)
        replies_pendientes = len(peers)

    multicast_request(timestamp, nombre)

    # Esperar N-1 REPLYs
    while replies_pendientes > 0:
        time.sleep(0.1)

    estado = HELD
    print(f"[{nombre}] Acceso autorizado al log.")

def acceso_log(nombre, mensaje):
    """Accede al log en el Host del Log."""
    global estado, log_local
    with socket.socket() as s:
        s.connect((HOST, PORT))
        s.sendall(f"AUTHENTICATE|{clave_secreta}".encode())
        respuesta = s.recv(1024).decode()

        if respuesta == 'AUTHSUCCESS':
            s.sendall(f"ADD_LOG|{mensaje}".encode())
            print(f"[{nombre}] Mensaje enviado al log: {mensaje}")
            estado = RELEASED
            procesar_cola_RA()
        else:
            print(f"[{nombre}] Error de autenticación.")

        # Esperar actualización del log
        estado_log = s.recv(1024).decode()
        if estado_log.startswith("NEW_LOG_STATE"):
            log_local = estado_log.split('|')[1:]
            print(f"[{nombre}] Log actualizado: {log_local}")

def procesar_cola_RA():
    """Procesa la cola de solicitudes pendientes."""
    global cola_RA
    for timestamp, peer in sorted(cola_RA):
        enviar_reply(peer)
    cola_RA.clear()

# Configuración inicial
nombre = input("Ingrese el nombre del Peer: ")
total_peers = int(input("Ingrese el número total de Peers: "))
for i in range(total_peers-1):
    peer_nombre = input(f"Ingrese el nombre del Peer {i+1}: ")
    peer_host = input("Ingrese el host del Peer: ")
    peer_port = int(input("Ingrese el puerto del Peer: "))
    peers.append((peer_nombre, peer_host, peer_port))

# Iniciar hilo para manejar conexiones entrantes
threading.Thread(target=manejar_conexiones, daemon=True).start()

# Menú principal
while True:
    print("\nOpciones:")
    print("1. Solicitar acceso al log")
    print("2. Salir")
    opcion = input("Seleccione una opción: ")

    if opcion == '1':
        mensaje = input("Ingrese el mensaje para el log: ")
        solicitar_acceso(nombre)
        acceso_log(nombre, mensaje)
    elif opcion == '2':
        break
    else:
        print("Opción inválida.")
