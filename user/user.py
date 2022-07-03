from fastapi import FastAPI
import json
import requests
from fastapi_utils.tasks import repeat_every
from sqlalchemy import true
import os

server_interface = FastAPI()   #La interfaz que se le brinda al cliente desarrollador.


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


def get_server(nickname: str):
  with open('./logged.json') as file:
    logged = json.load(file)
  server_list = logged["server_list"]
  url = server_list[0]
  prev = (requests.get('http://'+url+'/GetConnection', params= {"position": "previous"})).json()
  server = (requests.get('http://'+url+'/FindServer', params= {"user_nick": nickname, "who_asks": prev})).json()
  with open('./logged.json', 'w') as file:
    json.dump(logged, file)
  return server


@server_interface.post("/Login")  #Permite a un usuario Loguearse en el sistema.
def login(nickname: str, password: str, server: str):
  ip = server.split(":")[0] + ":8080"
  ping = (requests.get('http://'+ip+'/Active')).json()
  if not ping:
    return "Wrong server"
  logged = {}
  logged["my_nickname"] = nickname
  logged["server_list"] = [server]
  with open('./logged.json', 'w') as file:
    json.dump(logged, file)
  my_personal_server = get_server(nickname)
  password_check = (requests.get('http://'+my_personal_server+'/CheckPassword', params= {"nickname": nickname, "password": password})).json()
  if not password_check:
    if os.path.exists("logged.json"):
      os.remove("logged.json")
    return "Wrong password"
  
  return

@server_interface.post("/Logout")  #Permite cerrar la sesión del usuario.
def logout():
  if os.path.exists("logged.json"):
    os.remove("logged.json")
  return
  

@server_interface.post("/Register")   #Permite registrarse al usuario por primera vez en el sistema.
def register(name: str, nickname: str, password: str, server: str):
  ip = server.split(":")[0] + ":8080"
  ping = (requests.get('http://'+ip+'/Active')).json()
  if not ping:
    return "Wrong server"
  requests.post('http://'+server+'/RegisterUser', params= {"name": name, "nickname": nickname, "password": password})
  return


@server_interface.get("/Messages")  #Permite ver los mensajes entre "my_nickname" y "you_nickname".
def messages(user: str):
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  my_personal_server = get_server(my_nickname)
  contacts = (requests.get('http://'+my_personal_server+'/Contacts', params= {"nickname": my_nickname})).json()
  messages = []
  for key in contacts:
    if contacts[key] == user or key == user:
      messages = (requests.get('http://'+my_personal_server+'/GetMessages', params= {"my_nickname": my_nickname, "your_nickname": key})).json()
      break
  messages_format = []
  for message in messages:
    messages_format.append(message[0] + ": " + message[1])  
  return messages_format
  

@server_interface.post("/Send")
def send(user: str, message: str):
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  my_personal_server = get_server(my_nickname) 
  contacts = (requests.get('http://'+my_personal_server+'/Contacts', params= {"nickname": my_nickname})).json()
  for key in contacts:
    if contacts[key] == user:
      user = key
      break
  your_personal_server = get_server(user)
  if my_personal_server:
    requests.post('http://'+my_personal_server+'/SendMessage', params= {"my_nickname": my_nickname, "your_nickname": user, "message": message, "inherited": False})
  if your_personal_server and your_personal_server != my_personal_server:
    requests.post('http://'+your_personal_server+'/SendMessage', params= {"my_nickname": my_nickname, "your_nickname": user, "message": message, "inherited": False})
  return


def is_zombie_node(server: str):  
  next_1 = (requests.get('http://'+server+'/GetConnection', params= {"position": "next_1"})).json()
  if next_1: 
    return server != (requests.get('http://'+next_1+'/GetConnection', params= {"position": "previous"})).json()
  return False 


# @server_interface.on_event('startup')
# @repeat_every(seconds=10)
def update_server_list():
  with open('./logged.json') as file:
    logged = json.load(file)
  server_list = logged["server_list"]  
  new_list = []
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


@server_interface.post("/Add Contact")
def add_contact(nickname: str, name: str):
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  my_personal_server = get_server(my_nickname)
  requests.post('http://'+my_personal_server+'/AddContact', params= {"my_nickname": my_nickname, "contact_name": name, "your_nickname": nickname})
  return 


@server_interface.post("/Delete Contact")
def delete_contact(nickname: str):
  return add_contact(nickname, "Unknown")


@server_interface.get("/Contacts")
def contacts():
  my_nickname = check_login()
  if not my_nickname:
    return "You are not logged in"
  my_personal_server = get_server(my_nickname)
  contacts = (requests.get('http://'+my_personal_server+'/Contacts', params={"nickname": my_nickname})).json()
  contact_formats = []
  for nick in contacts:
    contact_formats.append(nick + ": " + contacts[nick])
  return contact_formats

