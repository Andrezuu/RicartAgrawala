import socket
import threading
from queue import Queue

HOST = 'localhost'
PORT = 5000
clave_secreta = 'clave123'

log = []
permiso_libre = True
ocupado_por = None
cola_espera = Queue()
clientes = {}  # map de nombre a socket

lock = threading.Lock()

def manejar_cliente(conn, addr):
    global permiso_libre, ocupado_por

    nombre = conn.recv(1024).decode()
    with lock:
        clientes[nombre] = conn
    print(f"{nombre} conectado desde {addr}")

    while True:
        try:
            datos = conn.recv(1024).decode()
            if not datos:
                break
            partes = datos.split('|')
            comando = partes[0]

            print(f"[Coordinador] Comando recibido de {nombre}: {comando}")
            with lock:
                if comando == 'REQUEST':
                    if permiso_libre:
                        print(f"[Coordinador] {nombre} ha accedido al log.")
                        permiso_libre = False
                        ocupado_por = nombre
                        conn.sendall('OK'.encode())
                    else:
                        if nombre not in cola_espera.queue and nombre != ocupado_por:
                            cola_espera.put(nombre)
                            conn.sendall('COLA'.encode())
                            print(f"[Coordinador] {nombre} está en la cola de espera.")
                        print(f"[Coordinador] Cola de espera: {list(cola_espera.queue)}")


                elif comando == 'AUTHENTICATE':
                    clave = partes[1]
                    if nombre == ocupado_por:
                        if clave == clave_secreta:
                            conn.sendall('AUTHSUCCESS'.encode())
                        else:
                            conn.sendall('AUTHFAIL'.encode())
                            permiso_libre = True
                            ocupado_por = None
                            procesar_cola()

                elif comando == 'APPEND':
                    mensaje = partes[1]
                    if nombre == ocupado_por:
                        log.append(f"{nombre}: {mensaje}")
                        conn.sendall('CONFIRMACION'.encode())
                        print("Log actualizado:", log)
                        permiso_libre = True
                        ocupado_por = None
                        procesar_cola()
        except:
            print(f"[Coordinador] Error al manejar el cliente {nombre}.")
            break

    conn.close()
    with lock:
        if nombre == ocupado_por:
            permiso_libre = True
            ocupado_por = None
            procesar_cola()
        print(f"{nombre} desconectado")
        if nombre in clientes:
            del clientes[nombre]

def procesar_cola():
    global permiso_libre, ocupado_por
    if not cola_espera.empty() and permiso_libre:
        siguiente = cola_espera.get()
        sock = clientes.get(siguiente)
        if sock:
            sock.sendall('OK'.encode())
            permiso_libre = False
            ocupado_por = siguiente

with socket.socket() as s:
    s.bind((HOST, PORT))
    s.listen()
    print(f"[Coordinador] Esperando conexiones en {HOST}:{PORT}...")

    while True:
        conn, addr = s.accept()
        threading.Thread(target=manejar_cliente, args=(conn, addr), daemon=True).start()
