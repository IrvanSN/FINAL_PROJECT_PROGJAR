import socket
import os
import threading
from tqdm import tqdm
import struct
import time

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

SESSION_UCAST_IP = ""
SESSION_UCAST_PORT = ""

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
    bar = tqdm(total=file_size, desc=f"Sending {file_name}", unit="B", unit_scale=True, unit_divisor=SIZE)
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

  ip = socket.gethostbyname(socket.gethostname())
  port = 10507

  s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  s.bind((ip, port))

  s.listen(1)

  print(f"IP: {ip}, PORT: {port}\n")

  print("Menunggu node penerima..\n")
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
  print("Menunggu file masuk..\n")
  data = s.recv(SIZE).decode(FORMAT)
  item = data.split("_")
  file_name = item[0]
  file_size = int(item[1])

  recv_filename = unique_filename(f"assets/received_{file_name}")
  with open(recv_filename, "wb") as f:
    bar = tqdm(total=file_size, desc=f"Receiving {file_name} as {recv_filename}", unit="B", unit_scale=True, unit_divisor=SIZE)
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
  global SESSION_UCAST_IP
  global SESSION_UCAST_PORT
  use_unicast_session = "n"

  s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

  if SESSION_UCAST_IP != "" and SESSION_UCAST_PORT != "":
    use_unicast_session = input(f"Gunakan alamat Unicast sebelumnya - {SESSION_UCAST_IP}:{SESSION_UCAST_PORT} (y/n): ")

  if (SESSION_UCAST_IP == "" or SESSION_UCAST_PORT == "") or use_unicast_session == "n":
    SESSION_UCAST_IP = input('Masukkan ip pengirim: ')
    SESSION_UCAST_PORT= int(input('Masukkan port pengirim: '))

  ip = SESSION_UCAST_IP
  port = SESSION_UCAST_PORT

  server_address = (ip, port)

  s.connect(server_address)

  print("")
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

SESSION_MCAST_SEND_TO_GROUP= ""
SESSION_MCAST_SEND_TO_PORT= ""
SESSION_MCAST_RECEIVER_GROUP = ""
SESSION_MCAST_RECEIVER_PORT = ""

def multicast_sender_chat(s, group_ip, group_port):
  message = input("Masukkan pesan: ")
  print("")
  s.sendto(message.encode(FORMAT), (group_ip, group_port))

  s.close()
  multicast()

def multicast_receiver_chat(s):
  print("Menunggu pesan masuk...\n")
  message, _ = s.recvfrom(SIZE)
  print("PESAN:", message.decode(FORMAT))
  print("")

  s.close()
  multicast()

def multicast_sender_files(s, group_ip, group_port):
  file_name = input("Masukkan nama file yang akan dikirimkan: ")
  file_size = os.path.getsize(file_name)
  print("")

  data = f"{file_name}_{file_size}"
  s.sendto(data.encode(FORMAT), (group_ip, group_port))

  with open(file_name, "rb") as f:
    bar = tqdm(total=file_size, desc=f"Sending {file_name}", unit="B", unit_scale=True, unit_divisor=SIZE)
    bytes_read = 0

    while bytes_read < file_size:
      data = f.read(SIZE)
      bytes_read += len(data)

      if not data:
        break

      s.sendto(data, (group_ip, group_port))
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
    bar = tqdm(total=file_size, desc=f"Receiving {file_name} as {recv_filename}", unit="B", unit_scale=True, unit_divisor=SIZE)
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
  global SESSION_MCAST_SEND_TO_GROUP
  global SESSION_MCAST_SEND_TO_PORT
  use_multicast_session = "n"
  ttl = 2

  if SESSION_MCAST_SEND_TO_GROUP != "" and SESSION_MCAST_SEND_TO_PORT != "":
    use_multicast_session = input(f"Gunakan tujuan Multicast sebelumnya - {SESSION_MCAST_SEND_TO_GROUP}:{SESSION_MCAST_SEND_TO_PORT} (y/n): ")

  if (SESSION_MCAST_SEND_TO_GROUP == "" or SESSION_MCAST_SEND_TO_PORT == "") or use_multicast_session == "n":
    print("Isi input dibawah ini untuk tujuan group Multicast")
    SESSION_MCAST_SEND_TO_GROUP = input("IP GROUP (239.0.0.0 - 239.255.255.255): ")
    SESSION_MCAST_SEND_TO_PORT = int(input("PORT GROUP: "))

  SEND_TO_GROUP = SESSION_MCAST_SEND_TO_GROUP
  SEND_TO_PORT = SESSION_MCAST_SEND_TO_PORT

  print("")

  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
  sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

  return sock, SEND_TO_GROUP, SEND_TO_PORT

def multicast_receiver_connect():
  global SESSION_MCAST_RECEIVER_GROUP
  global SESSION_MCAST_RECEIVER_PORT
  use_multicast_session = "n"

  if SESSION_MCAST_RECEIVER_GROUP != "" and SESSION_MCAST_RECEIVER_PORT != "":
    use_multicast_session = input(f"Gunakan alamat Multicast sebelumnya - {SESSION_MCAST_RECEIVER_GROUP}:{SESSION_MCAST_RECEIVER_PORT} (y/n): ")

  if (SESSION_MCAST_RECEIVER_GROUP == "" or SESSION_MCAST_RECEIVER_PORT == "") or use_multicast_session == "n":
    print("Isi input dibawah ini untuk alamat group Multicast")
    SESSION_MCAST_RECEIVER_GROUP = input("IP GROUP (239.0.0.0 - 239.255.255.255): ")
    SESSION_MCAST_RECEIVER_PORT = int(input("PORT GROUP: "))

  MCAST_GROUP = SESSION_MCAST_RECEIVER_GROUP
  MCAST_PORT = SESSION_MCAST_RECEIVER_PORT

  print("")
  
  sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) 

  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  sock.bind(('', MCAST_PORT))

  mreq = struct.pack("4sl", socket.inet_aton(MCAST_GROUP), socket.INADDR_ANY)

  sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

  return sock

def multicast():
  multicast_user_action = input_pick_action()
  print("")

  if multicast_user_action == "1":
    socket_connect, SEND_TO_GROUP, SEND_TO_PORT = multicast_sender_connect()
    multicast_sender_chat(socket_connect, SEND_TO_GROUP, SEND_TO_PORT)
  elif multicast_user_action == "2":
    socket_connect = multicast_receiver_connect()
    multicast_receiver_chat(socket_connect)
  elif multicast_user_action == "3":
    socket_connect, SEND_TO_GROUP, SEND_TO_PORT = multicast_sender_connect()
    multicast_sender_files(socket_connect, SEND_TO_GROUP, SEND_TO_PORT)
  elif multicast_user_action == "4":
    socket_connect = multicast_receiver_connect()
    multicast_receiver_files(socket_connect)
  elif multicast_user_action == "5":
    main()
  else:
    print("Keluar dari program.")
    exit()


CLIENTS = []
SESSION_BCAST_IP = "192.168.1.13"
SESSION_BCAST_PORT = 10507
RUNNING_THREAD = True

def broadcast_all_clients(message):
  clients_to_remove = []
  for client in CLIENTS:
    try:
      client.send(message)
    except:
      clients_to_remove.append(client)
  for client in clients_to_remove:
    client.close()
    CLIENTS.remove(client)

def server_send_message(s, message):
  global RUNNING_THREAD

  broadcast_all_clients(message.encode(FORMAT))
  print("")

  s.close()
  broadcast()
  RUNNING_THREAD = False

def server_send_files(s, file_name):
  global RUNNING_THREAD

  file_size = os.path.getsize(file_name)
  print("")

  data = f"{file_name}_{file_size}"
  broadcast_all_clients(data.encode(FORMAT))

  with open(file_name, "rb") as f:
    bar = tqdm(total=file_size, desc=f"Sending {file_name}", unit="B", unit_scale=True, unit_divisor=SIZE)
    bytes_read = 0

    while bytes_read < file_size:
      data = f.read(SIZE)
      bytes_read += len(data)

      if not data:
        break

      broadcast_all_clients(data)
      bar.update(len(data))

  bar.close()
  print("")

  s.close()
  broadcast()
  RUNNING_THREAD = False

def accept_connections(s):
  global RUNNING_THREAD

  try:
    while RUNNING_THREAD:
      conn, _ = s.accept()
      CLIENTS.append(conn)

  except ConnectionAbortedError as e:
    if e.errno != 53:
        raise

def broadcast_server_connect():
  global RUNNING_THREAD

  RUNNING_THREAD = True

  ip = socket.gethostbyname(socket.gethostname())
  port = 10507

  server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  server_socket.bind((ip, port))

  print(f"IP: {ip}, PORT: {port}\n")

  server_socket.listen()

  accept_thread = threading.Thread(target=accept_connections, args=(server_socket,))
  accept_thread.start()

  return server_socket

def client_receive_message(s):
  print("Menunggu pesan masuk..")
  message = s.recv(SIZE).decode(FORMAT)
  print("\nPESAN BROADCAST >>", message)
  print("")

  s.close()
  broadcast()

def client_receive_files(s):
  print("Menunggu file masuk..")
  data, _ = s.recvfrom(SIZE)
  item = data.decode(FORMAT).split("_")
  file_name = item[0]
  file_size = int(item[1])

  recv_filename = unique_filename(f"assets/received_{file_name}")
  with open(recv_filename, "wb") as f:
    bar = tqdm(total=file_size, desc=f"Receiving {file_name} as {recv_filename}", unit="B", unit_scale=True, unit_divisor=SIZE)
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

def broadcast_client_connect():
  global SESSION_BCAST_IP
  global SESSION_BCAST_PORT
  use_broadcast_session = "n"

  if SESSION_BCAST_IP != "" and SESSION_BCAST_PORT != "":
    use_broadcast_session = input(f"Gunakan alamat Broadcast sebelumnya - {SESSION_BCAST_IP}:{SESSION_BCAST_PORT} (y/n): ")

  if (SESSION_BCAST_IP == "" or SESSION_BCAST_PORT == "") or use_broadcast_session == "n":
    SESSION_BCAST_IP = input('Masukkan ip pengirim: ')
    SESSION_BCAST_PORT= int(input('Masukkan port pengirim: '))

  ip = SESSION_BCAST_IP
  port = SESSION_BCAST_PORT

  client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
  client_socket.connect((ip, port))

  return client_socket

def broadcast():
  print("===== Aksi =====")
  print("1. Kirim Pesan")
  print("2. Terima Pesan")
  print("3. Kirim File")
  print("4. Terima File")
  print("5. Back (Pilih Metode Komunikasi)")
  print("6. Exit (Keluar dari Program)")

  broadcast_user_action = input("Pilih aksi yang diinginkan: ")
  print("")

  if broadcast_user_action == "1":
    socket_connect = broadcast_server_connect()
    message = input("Masukkan pesan Broadcast: ")
    server_send_message(socket_connect, message)

  elif broadcast_user_action == "2":
    socket_connect = broadcast_client_connect()
    client_receive_message(socket_connect)

  elif broadcast_user_action == "3":
    socket_connect = broadcast_server_connect()
    file_name = input("Masukkan nama file yang akan dikirimkan: ")
    server_send_files(socket_connect, file_name)

  elif broadcast_user_action == "4":
    socket_connect = broadcast_client_connect()
    client_receive_files(socket_connect)

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