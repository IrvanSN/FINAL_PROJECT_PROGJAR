import socket
import os
import threading
from tqdm import tqdm
import struct

def unique_filename(filename):
  if not os.path.exists(filename):
    return filename

  filename, ext = os.path.splitext(filename)
  count = 1
  while os.path.exists(f"{filename}_{count}{ext}"):
    count += 1
  return f"{filename}_{count}{ext}"

def input_pick_action():
  print("===== Aksi =====")
  print("1. Kirim Pesan")
  print("2. Terima Pesan")
  print("3. Kirim File")
  print("4. Terima File")
  print("5. Back (Pilih Metode Komunikasi)")
  print("6. Exit (Keluar dari Program)")

  return input("Pilih aksi yang diinginkan: ")

SIZE = 1024
FORMAT = "utf-8"

SERVER_IP = "localhost"
SERVER_PORT = 23491

def unicast_server_chat(s):
  message = input("Ketikkan pesanmu: ")
  print("")
  s.send(message.encode(FORMAT))

  s.close()
  unicast()

def unicast_server_files(s):
  file_name = input("Masukkan nama file yang akan dikirimkan: ")
  file_size = os.path.getsize(file_name)

  data = f"{file_name}_{file_size}"
  s.send(data.encode(FORMAT))
  print("")

  with open(file_name, "rb") as f:
    bar = tqdm(total=file_size, desc=f"Sending {file_name}", unit="B", unit_scale=True, unit_divisor=1024)
    bytes_read = 0

    while bytes_read < file_size:
      data = f.read(SIZE)
      bytes_read += len(data)

      if not data:
        break

      s.send(data)

      msg = s.recv(SIZE).decode(FORMAT)
      bar.update(len(data))
    
  bar.close()
  print("")

  s.close()
  unicast()

def unicast_server_connect():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  hostname = SERVER_IP #socket.gethostname()
  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind((socket.gethostbyname(hostname), SERVER_PORT))

  s.listen(1)

  print("Menunggu node penerima pesan..\n")
  server_socket, addr = s.accept()
  print("Node penerima telah terkoneksi!\n")

  return server_socket

def unicast_client_chat(s):
  print("Menunggu pesan dari pengirim..\n")
  message = s.recv(SIZE).decode(FORMAT)
  print("PESAN:", message)
  print("")

  s.close()
  unicast()

def unicast_client_files(s):
  data = s.recv(SIZE).decode(FORMAT)
  item = data.split("_")
  file_name = item[0]
  file_size = int(item[1])

  recv_filename = unique_filename(f"assets/received_{file_name}")
  with open(recv_filename, "wb") as f:
    bar = tqdm(total=file_size, desc=f"Receiving {file_name} as {recv_filename}", unit="B", unit_scale=True, unit_divisor=1024)
    bytes_received = 0

    while bytes_received < file_size:
      data = s.recv(SIZE)
      bytes_received += len(data)

      if not data:
        break
      
      f.write(data)

      s.send("Data received.".encode(FORMAT))
      bar.update(len(data))
  
  bar.close()
  print("")

  s.close()
  unicast()

def unicast_client_connect():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  ip = SERVER_IP #input('Masukkan ip server: ')
  port = SERVER_PORT #int(input('Masukkan port server: '))

  server_address = (ip, port)

  s.connect(server_address)

  return s

def unicast():
  unicast_user_action = input_pick_action()
  print("")

  if unicast_user_action == "1":
    socket_connect = unicast_server_connect()
    unicast_server_chat(socket_connect)
  elif unicast_user_action == "2":
    socket_connect = unicast_client_connect()
    unicast_client_chat(socket_connect)
  elif unicast_user_action == "3":
    socket_connect = unicast_server_connect()
    unicast_server_files(socket_connect)
  elif unicast_user_action == "4":
    socket_connect = unicast_client_connect()
    unicast_client_files(socket_connect)
  elif unicast_user_action == "5":
    main()
  else:
    print("Keluar dari program.")
    exit()


MULTICAST_ADDR = '224.0.0.1'
MULTICAST_PORT = 55555

def multicast_sender_chat(s):
  message = input("SENDER: ")
  print("")
  s.sendto(message.encode(FORMAT), (MULTICAST_ADDR, MULTICAST_PORT))
  s.close()
  multicast()

def multicast_receiver_chat(s):
  print("Menunggu pesan masuk...\n")
  message, _ = s.recvfrom(SIZE)
  print("MESSAGE:", message.decode(FORMAT))
  print("")
  s.close()
  multicast()

def multicast_sender_files(s):
  file_name = input("Masukkan nama file yang akan dikirimkan: ")
  file_size = os.path.getsize(file_name)
  print("")

  data = f"{file_name}_{file_size}"
  s.sendto(data.encode(FORMAT), (MULTICAST_ADDR, MULTICAST_PORT))

  with open(file_name, "rb") as f:
    bar = tqdm(total=file_size, desc=f"Sending {file_name}", unit="B", unit_scale=True, unit_divisor=1024)
    bytes_read = 0

    while bytes_read < file_size:
      data = f.read(SIZE)
      bytes_read += len(data)

      if not data:
        break

      s.sendto(data, (MULTICAST_ADDR, MULTICAST_PORT))
      bar.update(len(data))

  bar.close()
  print("")
  s.close()
  multicast()

def multicast_receiver_files(s):
  print("Menunggu file masuk..\n")
  data, _ = s.recvfrom(SIZE)
  item = data.decode(FORMAT).split("_")
  file_name = item[0]
  file_size = int(item[1])

  recv_filename = unique_filename(f"assets/received_{file_name}")
  with open(recv_filename, "wb") as f:
    bar = tqdm(total=file_size, desc=f"Receiving {file_name} as {recv_filename}", unit="B", unit_scale=True, unit_divisor=1024)
    bytes_received = 0

    while bytes_received < file_size:
      data, _ = s.recvfrom(SIZE)
      bytes_received += len(data)

      if not data:
        break
      
      f.write(data)
      bar.update(len(data))

  bar.close()
  print("")
  s.close()
  multicast()

def multicast_sender_connect():
  ttl = 2

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

  return sock

def multicast_receiver_connect():
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 

  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.bind(('', MULTICAST_PORT))

  mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)

  sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

  return sock

def multicast():
  multicast_user_action = input_pick_action()
  print("")

  if multicast_user_action == "1":
    socket_connect = multicast_sender_connect()
    multicast_sender_chat(socket_connect)
  elif multicast_user_action == "2":
    socket_connect = multicast_receiver_connect()
    multicast_receiver_chat(socket_connect)
  elif multicast_user_action == "3":
    socket_connect = multicast_sender_connect()
    multicast_sender_files(socket_connect)
  elif multicast_user_action == "4":
    socket_connect = multicast_receiver_connect()
    multicast_receiver_files(socket_connect)
  elif multicast_user_action == "5":
    main()
  else:
    print("Keluar dari program.")
    exit()


CLIENTS = []
BROADCAST_HOST = '127.0.0.1'
BROADCAST_PORT = 12341

def broadcast_all_client(message):
  clients_to_remove = []
  for client in CLIENTS:
    try:
      client.send(message)
    except:
      clients_to_remove.append(client)
  for client in clients_to_remove:
    client.close()
    CLIENTS.remove(client)

def server_send_message(s):
  message = input("Masukkan pesan Broadcast: ")
  print("")
  broadcast_all_client(message.encode(FORMAT))
  s.close()
  broadcast()

def server_send_files(s):
  file_name = input("Masukkan nama file yang akan dikirimkan: ")
  file_size = os.path.getsize(file_name)
  print("")

  data = f"{file_name}_{file_size}"
  broadcast_all_client(data.encode(FORMAT))

  with open(file_name, "rb") as f:
    bar = tqdm(total=file_size, desc=f"Sending {file_name}", unit="B", unit_scale=True, unit_divisor=1024)
    bytes_read = 0

    while bytes_read < file_size:
      data = f.read(SIZE)
      bytes_read += len(data)

      if not data:
        break

      broadcast_all_client(data)
      bar.update(len(data))

  bar.close()
  print("")
  s.close()
  broadcast()

def broadcast_chat_send_thread(s):
  try:
    send_thread = threading.Thread(target=server_send_message, args=(s,))
    send_thread.start()

    while True:
      conn, _ = s.accept()
      CLIENTS.append(conn)
  except ConnectionAbortedError as e:
    if e.errno != 53:
        raise

def broadcast_file_send_thread(s):
  try:
    send_thread = threading.Thread(target=server_send_files, args=(s,))
    send_thread.start()

    while True:
      conn, _ = s.accept()
      CLIENTS.append(conn)
  except ConnectionAbortedError as e:
    if e.errno != 53:
        raise

def broadcast_server_connect():
  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server_socket.bind((BROADCAST_HOST, BROADCAST_PORT))

  server_socket.listen()

  return server_socket

def client_receive_message(s):
  try:
    print("Menunggu pesan masuk..")
    message = s.recv(1024).decode('utf-8')
    print("\nPESAN BROADCAST >>", message)
    print("")
  except:
    pass
  finally:
    broadcast()
    s.close()

def client_receive_files(s):
  print("Menunggu file masuk..")
  data, _ = s.recvfrom(SIZE)
  item = data.decode(FORMAT).split("_")
  file_name = item[0]
  file_size = int(item[1])

  recv_filename = unique_filename(f"assets/received_{file_name}")
  with open(recv_filename, "wb") as f:
    bar = tqdm(total=file_size, desc=f"Receiving {file_name} as {recv_filename}", unit="B", unit_scale=True, unit_divisor=1024)
    bytes_received = 0

    while bytes_received < file_size:
      data, _ = s.recvfrom(SIZE)
      bytes_received += len(data)

      if not data:
        break
      
      f.write(data)
      bar.update(len(data))

  bar.close()
  print("")
  s.close()
  broadcast()

def broadcast_chat_receive_thread(s):
  receive_thread = threading.Thread(target=client_receive_message, args=(s,))
  receive_thread.start()

def broadcast_file_receive_thread(s):
  receive_thread = threading.Thread(target=client_receive_files, args=(s,))
  receive_thread.start()

def broadcast_client_connect():
  client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client_socket.connect((BROADCAST_HOST, BROADCAST_PORT))

  return client_socket

def broadcast():
  broadcast_user_action = input_pick_action()
  print("")

  if broadcast_user_action == "1":
    socket_connect = broadcast_server_connect()
    broadcast_chat_send_thread(socket_connect)
  if broadcast_user_action == "2":
    socket_connect = broadcast_client_connect()
    broadcast_chat_receive_thread(socket_connect)
  elif broadcast_user_action == "3":
    socket_connect = broadcast_server_connect()
    broadcast_file_send_thread(socket_connect)
  elif broadcast_user_action == "4":
    socket_connect = broadcast_client_connect()
    broadcast_file_receive_thread(socket_connect)
  elif broadcast_user_action == "5":
    main()
  else:
    print("Keluar dari program.")
    exit()

def main():
  print("===== Metode Komunikasi =====")
  print("1. Unicast")
  print("2. Multicast")
  print("3. Broadcast")
  print("4. Exit (Keluar dari Program)")

  method = input("Pilih metode komunikasi sesuai huruf diatas: ")
  print("")

  if method == "1":
    unicast()
  elif method == "2":
    multicast()
  elif method == "3":
    broadcast()
  else:
    print("Keluar dari program.")
    exit()

main()