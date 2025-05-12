import socket
import json
import sys
import time

host = 'localhost'
port = 6000
secret_key = "secret123"  

log = []

authenticated_peers = set()


peer_addresses = {}


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((host, port))
print(f"Host del Log iniciado en {host}:{port}")


def broadcast_log_state():
    message = {
        "type": "NEW_LOG_STATE",
        "sender": -1,  # -1 representa el host del log
        "clock": int(time.time()),
        "payload": {
            "log": log
        }
    }
    
    json_message = json.dumps(message).encode()
    for addr in peer_addresses.values():
        sock.sendto(json_message, addr)
    
    print(f"Estado del log enviado a {len(peer_addresses)} peers")

try:
    print("Host del Log ejecutándose. Presiona Ctrl+C para salir.")
    print("Esperando mensajes de los peers...")
    
    while True:
        data, addr = sock.recvfrom(4096)
        message = json.loads(data.decode())
        
        sender_id = message["sender"]
        peer_addresses[sender_id] = addr
        
        msg_type = message["type"]
        
        if msg_type == "AUTHENTICATE":
            key = message["payload"]["key"]
            print(f"Solicitud de autenticación de Peer {sender_id}")
            
            if key == secret_key:
                authenticated_peers.add(sender_id)
                print(f"Peer {sender_id} autenticado correctamente")
            else:
                print(f"Autenticación fallida para Peer {sender_id}")
                # Enviar mensaje de error
                error_message = {
                    "type": "ERROR",
                    "sender": -1,
                    "clock": int(time.time()),
                    "payload": {
                        "message": "Autenticación fallida"
                    }
                }
                sock.sendto(json.dumps(error_message).encode(), addr)
                
        elif msg_type == "ADD_LOG":
            # Procesar solicitud para añadir al log
            if sender_id in authenticated_peers:
                log_message = message["payload"]["message"]
                log.append({
                    "time": time.time(),
                    "peer": sender_id,
                    "message": log_message
                })
                
                print(f"Añadida entrada al log de Peer {sender_id}: {log_message}")
                print(f"Log actual: {log}")
                
                # Limpiar autenticación después de usarla
                authenticated_peers.remove(sender_id)
                
                # Enviar log actualizado a todos los peers
                broadcast_log_state()
            else:
                print(f"Intento de añadir al log sin autenticación de Peer {sender_id}")
                # Enviar mensaje de error
                error_message = {
                    "type": "ERROR",
                    "sender": -1,
                    "clock": int(time.time()),
                    "payload": {
                        "message": "No autenticado"
                    }
                }
                sock.sendto(json.dumps(error_message).encode(), addr)
                
        else:
            print(f"Recibido tipo de mensaje desconocido: {msg_type}")

except KeyboardInterrupt:
    print("\nHost del Log cerrando")
    sock.close()
    sys.exit(0)