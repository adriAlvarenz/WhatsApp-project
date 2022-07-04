from fastapi import FastAPI
import json
import requests
from fastapi_utils.tasks import repeat_every
from sqlalchemy import true
import os

server_interface = FastAPI()   #La interfaz que se le brinda al cliente.

#chequea si el usuario está loggeado
def check_login():
  if not os.path.exists("logged.json"):
    return ""
  with open('./logged.json') as file:
    logged = json.load(file)
  my_nickname = logged["my_nickname"] 
  with open('./logged.json', 'w') as file:
    json.dump(logged, file)
  if not my_nickname:
    return ""
  return my_nickname

#se busca el server que me contiene
def get_server(nickname: str):
  with open('./logged.json') as file:
    logged = json.load(file)
  #se lee la server list del usuario loggeado
  server_list = logged["server_list"]
  #se coge un servidor de la lista
  url = server_list[0]
  #se busca el previo del servidor
  prev = (requests.get('http://'+url+'/GetConnection', params= {"position": "previous"})).json()
  #se llama a findserver con el previo del servidor. Se empieza desde el previo para revisar también su next1, revisar FindServer si hay dudas
  server = (requests.get('http://'+url+'/FindServer', params= {"user_nick": nickname, "who_asks": prev})).json()
  with open('./logged.json', 'w') as file:
    json.dump(logged, file)
  return server


#Permite a un usuario Loguearse en el sistema.
@server_interface.post("/Login")
def login(nickname: str, password: str, server: str):
  #se verifica que el servidor al que se está intentando conectar es accesible
  ip = server.split(":")[0] + ":8080"
  ping = (requests.get('http://'+ip+'/Active')).json()
  if not ping:
    return "Wrong server"
  #se crea el archivo logged para el usuario con su nickname y su server list con el servidor al que se conectó
  logged = {}
  logged["my_nickname"] = nickname
  logged["server_list"] = [server]
  with open('./logged.json', 'w') as file:
    json.dump(logged, file)
  my_personal_server = get_server(nickname)
  #se chequea que la contraseña sea correcta
  password_check = (requests.get('http://'+my_personal_server+'/CheckPassword', params= {"nickname": nickname, "password": password})).json()
  if not password_check:
    if os.path.exists("logged.json"):
      os.remove("logged.json")
    return "Wrong password"
  return


#Permite cerrar la sesión del usuario. Elimina su json de loggeado
@server_interface.post("/Logout")  
def logout():
  if os.path.exists("logged.json"):
    os.remove("logged.json")
  return
  

#Permite registrarse al usuario por primera vez en el sistema.
@server_interface.post("/Register")   
def register(name: str, nickname: str, password: str, server: str):
  #se verifica que el servidor al que se intenta acceder sea accesible
  ip = server.split(":")[0] + ":8080"
  ping = (requests.get('http://'+ip+'/Active')).json()
  if not ping:
    return "Wrong server"
  #en caso afirmativo se manda a registrar este usuario con la información recibida
  requests.post('http://'+server+'/RegisterUser', params= {"name": name, "nickname": nickname, "password": password})
  return


#Permite ver los mensajes entre "my_nickname" y "you_nickname".
@server_interface.get("/Messages")  
def messages(user: str):
  #se chequea que el usuario esté loggeado
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  #se busca el servidor en que está almacenada la información del usuario
  my_personal_server = get_server(my_nickname)
  #obtener los contactos que tengo 
  contacts = (requests.get('http://'+my_personal_server+'/Contacts', params= {"nickname": my_nickname})).json()
  messages = []
  #verificar si tengo entre mis contactos a la persona de la cual quiero ver los mensajes que tenemos
  for key in contacts:
    #verifico si el nombre dado es el nick o el nombre con el que lo tengo registrado
    if contacts[key] == user or key == user:
      #mando a buscar los mensajes al servidor
      messages = (requests.get('http://'+my_personal_server+'/GetMessages', params= {"my_nickname": my_nickname, "your_nickname": key})).json()
      break
  #para ver mejor los mensajes
  messages_format = []
  for message in messages:
    messages_format.append(message[0] + ": " + message[1])  
  return messages_format
  

#para enviar mensajes a otro usuario
@server_interface.post("/Send")
def send(user: str, message: str):
  #se chequea que yo esté loggeado
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  #se obtiene el server que tiene mi data
  my_personal_server = get_server(my_nickname) 
  #busco mi lista de contactos
  contacts = (requests.get('http://'+my_personal_server+'/Contacts', params= {"nickname": my_nickname})).json()
  #verifico si el nombre que se dió es el nick o el nombre de contacto, sustituyo por el nick en caso de ser el segundo
  for key in contacts:
    if contacts[key] == user:
      user = key
      break
  #busco el servidor que almacena la info del otro usuario
  your_personal_server = get_server(user)
  #si mi server está activo le mando el mensaje para ser escrito como data propio
  if my_personal_server:
    requests.post('http://'+my_personal_server+'/SendMessage', params= {"my_nickname": my_nickname, "your_nickname": user, "message": message, "inherited": False})
  #si su servidor está activo y no es mi mismo servidor hago lo mismo. Si somos del mismo server ya su info se escribió
  if your_personal_server and your_personal_server != my_personal_server:
    requests.post('http://'+your_personal_server+'/SendMessage', params= {"my_nickname": my_nickname, "your_nickname": user, "message": message, "inherited": False})
  return


#chequear si hay un server desconectado
def is_zombie_node(server: str): 
  #se obtiene el último next1 que registró en su tabla
  next_1 = (requests.get('http://'+server+'/GetConnection', params= {"position": "next_1"})).json()
  if next_1: 
    #si ese que el tiene registrado como next1 no lo tiene a él como previo, significa que él es un zombie
    return server != (requests.get('http://'+next_1+'/GetConnection', params= {"position": "previous"})).json()
  return False 

#VERIFICAR ESTAS DOS LINEAS COMENTADAS POSIBLE CAUSA DE ERROR
# @server_interface.on_event('startup')
# @repeat_every(seconds=10)
#actualiza la server list de un usuario loggeado
def update_server_list():
  with open('./logged.json') as file:
    logged = json.load(file)
  server_list = logged["server_list"]  
  new_list = []
  #la nueva lista se crea con el primer nodo de la anterior que no sea zombie y su sucesor
  while len(server_list):
    server = server_list.pop()
    if not is_zombie_node(server):
      new_list.append(server)
      next_server = (requests.get('http://'+server+'/DiscoverNext')).json()
      if next_server:
        new_list.append(next_server)
        break
  logged["server_list"] = new_list
  with open('./logged.json', 'w') as file:
    json.dump(logged, file)
  return


#para agregar un contacto
@server_interface.post("/Add Contact")
def add_contact(nickname: str, name: str):
  #chequear que el usuario este loggeado
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  #buscar el server en el que está la info de este usuario
  my_personal_server = get_server(my_nickname)
  #agregar el contacto
  requests.post('http://'+my_personal_server+'/AddContact', params= {"my_nickname": my_nickname, "contact_name": name, "your_nickname": nickname})
  return 


#eliminar es editar con nombre de contacto Unknown. Ver código del endpoint AddContact si hay dudas
@server_interface.post("/Delete Contact")
def delete_contact(nickname: str):
  return add_contact(nickname, "Unknown")

#ver lista de contactos
@server_interface.get("/Contacts")
def contacts():
  #chequear que el usuario esté loggeado
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  #buscar el server donde está la info de este usuario
  my_personal_server = get_server(my_nickname)
  #obtener de este server la lista de contactos de este usuario
  contacts = (requests.get('http://'+my_personal_server+'/Contacts', params={"nickname": my_nickname})).json()
  #se pone de manera cómoda a la lectura del usuario
  contact_formats = []
  for nick in contacts:
    contact_formats.append(nick + ": " + contacts[nick])
  return contact_formats

