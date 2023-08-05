import socket
import os
import threading
from tqdm import tqdm
import struct
import select
import sys

SIZE = 1024
FORMAT = "utf-8"

SERVER_IP = "localhost"
SERVER_PORT = 23491

def unique_filename(filename):
  if not os.path.exists(filename):
    return filename

  filename, ext = os.path.splitext(filename)
  count = 1
  while os.path.exists(f"{filename}_{count}{ext}"):
    count += 1
  return f"{filename}_{count}{ext}"

def unicast_server():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  hostname = SERVER_IP #socket.gethostname()
  s.bind((socket.gethostbyname(hostname), SERVER_PORT))

  s.listen(1)
  print(f"Server listening on {socket.gethostbyname(hostname)}:{SERVER_PORT}")

  server, address = s.accept()
  print("Terhubung dengan client: ", address)

  return server

def unicast_client():
  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  ip = SERVER_IP #input('Masukkan ip server: ')
  port = SERVER_PORT #int(input('Masukkan port server: '))

  server_address = (ip, port)

  s.connect(server_address)

  return s

def sender_chat(s):
  while True:
    message = input("Client: ")
    s.send(message.encode('utf-8'))
    if message.lower() == 'quit':
      print("Exiting conversation...")
      client_picking_feature(s)
      break

    response = s.recv(1024).decode('utf-8')
    print("Server:", response)
    if response.lower() == 'quit':
      print("Server terminated the conversation.")
      client_picking_feature(s)
      break

def receiver_chat(s):
  while True:
    message = s.recv(1024).decode('utf-8')
    if message.lower() == 'quit':
      print("Connection terminated by client.")
      server_picking_feature(s)
      break
    elif message:
      print("Client:", message)
      reply = input("Server: ")
      s.send(reply.encode('utf-8'))
      if reply.lower() == 'quit':
        print("Exiting conversation...")
        server_picking_feature(s)
        break

def sender_files(s):
  file_name = input("\nMasukkan nama file yang akan dikirimkan: ")
  file_size = os.path.getsize(file_name)

  data = f"{file_name}_{file_size}"
  s.send(data.encode(FORMAT))
  msg = s.recv(SIZE).decode(FORMAT)
  print(f"\nINFO: {msg}\n")

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
  client_picking_feature(s)

def receiver_files(s):
  data = s.recv(SIZE).decode(FORMAT)
  item = data.split("_")
  file_name = item[0]
  file_size = int(item[1])

  print("[+] Filename and filesize received\n")
  s.send("Filename and filesize received".encode(FORMAT))

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
  server_picking_feature(s)

def show_feature():
  print("===== Fitur =====")
  print("1. Chat")
  print("2. File")
  print("3. Exit")

  return input("Masukkan pilihan fitur (angka): ")

def sender_feature_handling(s, id):
  if id == "1":
    sender_chat(s)
  elif id == "2":
    sender_files(s)

def receiver_feature_handling(s, id):
  if id == "1":
    receiver_chat(s)
  elif id == "2":
    receiver_files(s)

def server_picking_feature(s):
  print("\nMenunggu client untuk memilih fitur...\n")
  selected_feature = s.recv(SIZE).decode(FORMAT)
  if selected_feature == "-":
    print("Client meminta server untuk memilih fitur...\n")
    selected_feature = show_feature()
    if selected_feature in ["1", "2"]:
      s.send(selected_feature.encode(FORMAT))
      sender_feature_handling(s, selected_feature)
    elif selected_feature == "-":
      s.send("switch".encode(FORMAT))
      server_picking_feature(s)
    else:
      print("\nKeluar dari program!")
      s.send("close".encode(FORMAT))
      s.close()
  elif selected_feature in ["1", "2"]:
    receiver_feature_handling(s, selected_feature)
    print(f"Client memilih fitur: {selected_feature}")
  else:
    print("Keluar dari program!")
    s.close()

def client_picking_feature(s):
  selected_feature = show_feature()
  if selected_feature == "-":
    s.send(selected_feature.encode())

    print("\nMenunggu server untuk memilih fitur...\n")
    selected_feature = s.recv(SIZE).decode(FORMAT)
    if selected_feature in ["1", "2"]:
      receiver_feature_handling(s, selected_feature)
      print(f"Server memilih fitur: {selected_feature}\n")
    elif selected_feature == "switch":
      client_picking_feature(s)
    else:
      print("Keluar dari program!")
      s.close()
  elif selected_feature in ["1", "2"]:
    s.send(selected_feature.encode())
    sender_feature_handling(s, selected_feature)
  else:
    print("\nKeluar dari program!")
    s.close()
    exit()

def unicast():
  print("===== User =====")
  print("1. Server")
  print("2. Client")
  print("3. Exit")

  selected_user = input("Pilih sebagai user (angka): ")
  print("")

  if selected_user == "1":
    server_socket = unicast_server()

    server_picking_feature(server_socket)
    
  elif selected_user == "2":
    client_socket = unicast_client()
    
    client_picking_feature(client_socket)

  else:
    exit()

MULTICAST_ADDR = '224.0.0.1'
MULTICAST_PORT = 55555

def multicast_sender():
  ttl = 2

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

  return sock

def multicast_receiver():
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 

  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.bind(('', MULTICAST_PORT))

  mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_ADDR), socket.INADDR_ANY)

  sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

  return sock

def multicast_pick_feature(s, type):
  selected_feature = show_feature()

  if type == "sender":
    if selected_feature == "1":
        multicast_sender_chat(s)
    elif selected_feature == "2":
      multicast_sender_files(s)
  elif type == "receiver":
    if selected_feature == "1":
        multicast_receiver_chat(s)
    elif selected_feature == "2":
      multicast_receiver_files(s)

def multicast_sender_chat(s):
  while True:
    message = input("SENDER: ")
    s.sendto(message.encode(FORMAT), (MULTICAST_ADDR, MULTICAST_PORT))
    if message.lower() == 'quit':
      print("Mengakhiri obrolan...")
      break

  multicast_pick_feature(s, "sender")

def multicast_receiver_chat(s):
  while True:
    print("\nMenunggu pesan masuk...")
    message, _ = s.recvfrom(SIZE)
    print("MESSAGE:", message.decode(FORMAT))
    if message.decode(FORMAT).lower() == 'quit':
      print("SENDER mengakhiri obrolan!")
      break
  
  multicast_pick_feature(s, "receiver")

def multicast_sender_files(s):
    file_name = input("\nMasukkan nama file yang akan dikirimkan: ")
    file_size = os.path.getsize(file_name)

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
    multicast_pick_feature(s, "sender")

def multicast_receiver_files(s):
    data, _ = s.recvfrom(SIZE)
    item = data.decode(FORMAT).split("_")
    file_name = item[0]
    file_size = int(item[1])

    print("[+] Filename and filesize received\n")

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
    multicast_pick_feature(s, "receiver")

def multicast():
  print("===== User =====")
  print("1. Receiver")
  print("2. Sender")
  print("3. Exit")

  selected_user = input("Pilih sebagai user (angka): ")
  print("")

  if selected_user == "1":
    receiver_socket = multicast_receiver()

    multicast_pick_feature(receiver_socket, "receiver")
    
  elif selected_user == "2":
    sender_socket = multicast_sender()
    
    multicast_pick_feature(sender_socket, "sender")
    
  else:
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
  print("===== Aksi =====")
  print("1. Kirim Pesan")
  print("2. Terima Pesan")
  print("3. Kirim File")
  print("4. Terima File")
  print("5. Exit")

  user_action = input("Masukkan aksi yang diinginkan: ")
  print("")

  if user_action == "1":
    socket_connect = broadcast_server_connect()
    broadcast_chat_send_thread(socket_connect)
  if user_action == "2":
    socket_connect = broadcast_client_connect()
    broadcast_chat_receive_thread(socket_connect)
  elif user_action == "3":
    socket_connect = broadcast_server_connect()
    broadcast_file_send_thread(socket_connect)
  elif user_action == "4":
    socket_connect = broadcast_client_connect()
    broadcast_file_receive_thread(socket_connect)
  elif user_action == "5":
    exit()


print("===== Metode Komunikasi =====")
print("1. Unicast")
print("2. Multicast")
print("3. Broadcast")

method = input("Pilih metode komunikasi sesuai huruf diatas: ")
print("")

if method == "1":
  unicast()
elif method == "2":
  multicast()
elif method == "3":
  broadcast()