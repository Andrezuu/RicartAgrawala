import socket
import json
import time
import threading
import sys

if len(sys.argv) < 3:
    print("Uso: python peer.py <id_peer> <total_peers>")
    sys.exit(1)

print(sys.argv)
peer_id = int(sys.argv[1])
total_peers = int(sys.argv[2])
secret_key = "secret123"  

host = 'localhost'
base_port = 5000  
log_host = 'localhost'
log_port = 6000

state = "RELEASED"
lamport_clock = 0
request_timestamp = (0, peer_id)  
replies_received = set()
deferred_replies = []

log = []


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, base_port + peer_id))
print(f"Peer {peer_id} iniciado en puerto {base_port + peer_id}")

def send_message(dest_id, msg_type, payload=None):
    global lamport_clock
    lamport_clock+=1
    if dest_id < 0:  # Log host
        dest_addr = (log_host, log_port)
    else:
        dest_addr = (host, base_port + dest_id)
        
    message = {
        "type": msg_type,
        "sender": peer_id,
        "clock": lamport_clock,
        "payload": payload or {}
    }
    
    sock.sendto(json.dumps(message).encode(), dest_addr)
    print(f"Enviado {msg_type} a {'Log Host' if dest_id < 0 else f'Peer {dest_id}'}")

def broadcast_message(msg_type, payload=None):
    for pid in range(total_peers):
        if pid != peer_id:
            send_message(pid, msg_type, payload)

def request_critical_section():
    global state, request_timestamp, replies_received
    
    if state != "RELEASED":
        print("Ya estás intentando acceder a sección crítica o ya estás en ella")
        return
        
    print("Solicitando acceso a sección crítica")
    state = "WANTED"
    request_timestamp = (lamport_clock, peer_id)
    replies_received = set()
    
    broadcast_message("REQUEST", {
        "timestamp": request_timestamp
    })
    
    print("Esperando respuestas...")
    while len(replies_received) < total_peers - 1:
        time.sleep(0.1)
        
    print("Entrando a sección crítica")
    state = "HELD"
    
    access_log(f"Mensaje de Peer {peer_id} en tiempo {time.time()}")

def release_critical_section():
    global state, deferred_replies
    
    if state != "HELD":
        print("No estás en sección crítica")
        return
        
    print("Liberando sección crítica")
    state = "RELEASED"
    
    # Enviar respuestas pendientes
    for pid in deferred_replies:
        send_message(pid, "REPLY")
    deferred_replies = []
    print("Sección crítica liberada y respuestas pendientes enviadas")

def access_log(message):
    # Autenticar con host de log
    send_message(-1, "AUTHENTICATE", {"key": secret_key})
    time.sleep(0.5)  # Espera simple para asegurar que la autenticación se procese
    
    # Añadir mensaje al log
    message = input("Introduce el mensaje a añadir al log: ")
    send_message(-1, "ADD_LOG", {"message": message})

# ---- Función para procesar solicitudes recibidas ----
def process_request(sender_id, timestamp):
    global deferred_replies
    
    ts_received = tuple(timestamp)  # Convertir lista a tupla para comparación
    
    if state == "HELD" or (state == "WANTED" and request_timestamp < ts_received):
        # Postergar respuesta
        deferred_replies.append(sender_id)
        print(f"Respuesta a Peer {sender_id} pospuesta")
    else:
        # Enviar respuesta inmediatamente
        send_message(sender_id, "REPLY")

# ---- Función para recibir mensajes ----
def receive_messages():
    global replies_received, log, lamport_clock
    
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            message = json.loads(data.decode())
            
            lamport_clock = max(lamport_clock, message["clock"]) + 1
            msg_type = message["type"]
            sender = message["sender"]
            
            if msg_type == "REQUEST":
                ts = message["payload"]["timestamp"]
                print(f"Recibido REQUEST de Peer {sender} con timestamp {ts}")
                process_request(sender, ts)
                
            elif msg_type == "REPLY":
                print(f"Recibido REPLY de Peer {sender}")
                replies_received.add(sender)
                
            elif msg_type == "NEW_LOG_STATE":
                log = message["payload"]["log"]
                print(f"Recibido NEW_LOG_STATE. Log tiene {len(log)} entradas.")
                print(f"Log actual: {log}")
                
            elif msg_type == "ERROR":
                print(f"ERROR del servidor: {message['payload']['message']}")
                
            else:
                print(f"Recibido tipo de mensaje desconocido: {msg_type}")
                
        except Exception as e:
            print(f"Error recibiendo mensaje: {e}")

receiver_thread = threading.Thread(target=receive_messages, daemon=True).start()

def show_menu():
    print("\n--- Menú Peer", peer_id, "---")
    print("1. Solicitar acceso al log (sección crítica)")
    print("2. Liberar sección crítica")
    print("3. Mostrar estado actual")
    print("4. Mostrar log actual")
    print("0. Salir")
    return input("Selecciona una opción: ")

try:
    while True:
        option = show_menu()
        
        if option == "1":
            request_critical_section()
        elif option == "2":
            release_critical_section()
        elif option == "3":
            print(f"\nEstado actual: {state}")
            print(f"Reloj de Lamport: {lamport_clock}")
            print(f"Timestamp de solicitud: {request_timestamp}")
            print(f"Respuestas recibidas: {replies_received}")
            print(f"Respuestas diferidas: {deferred_replies}")
        elif option == "4":
            print(f"\nLog actual ({len(log)} entradas):")
            for idx, entry in enumerate(log):
                print(f"{idx+1}. De Peer {entry['peer']}: {entry['message']}")
        elif option == "0":
            break
        else:
            print("Opción no válida")
            
except KeyboardInterrupt:
    print("\nSaliendo...")

print(f"Peer {peer_id} cerrando")
sock.close()
sys.exit(0)