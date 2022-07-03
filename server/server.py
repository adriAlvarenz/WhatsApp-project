from bleach import clean
from fastapi import FastAPI
import json
import requests 
from fastapi_utils.tasks import repeat_every
from sqlalchemy import false
from urllib3 import Retry

service = FastAPI(docs_url=None)

connection_servers = FastAPI()  #Conexión entre los servidores.


@connection_servers.post("/RegisterUser")
def register_user(name: str, nickname: str, password: str, inherited=False):
  with open('./connections.json') as file:
      data = json.load(file)
  check = (requests.get('http://'+data["me"]+'/FindServer', params= {"user_nick": nickname, "who_asks": data["previous"]})).json()
  with open('./connections.json', 'w') as file:
      json.dump(data, file)
  if not inherited and check:
    return "You are already registered"
  if not inherited:
    with open('./personal_data.json') as file_p:
      data = json.load(file_p)
  else:
    with open('./inherited_data.json') as file_h:
      data = json.load(file_h)      
  data['users'].append({
    'name': name, 
    'nickname': nickname,
    'password': password,
    'contacts': {},
    'messages':{}})
  if not inherited:
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data, file_p)   
    with open('./connections.json') as file:
      data = json.load(file)
    if data["next_1"] and ping(data["next_1"]) == 200:
      requests.post('http://'+data["next_1"]+'/RegisterUser', params= {"name": name, "nickname": nickname, "password": password, "inherited": True})
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
  else:
    with open('./inherited_data.json', 'w') as file_h:
      json.dump(data, file_h)
  return


@connection_servers.post("/Connect")
def connect(url: str):
  # Para abrir el .json
  with open('./connections.json') as file:
    data = json.load(file)
  if isconnect(url,data['previous']):
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    return
  password = data["password"]

  #Mi anterior es al que me quiero conectar.
  data['previous'] = url

  #Mi siguiente es el siguiente del nodo al que me quiero conectar, es decir, me pongo en el medio entre ellos.
  data['next_1'] = (requests.get('http://'+url+'/GetConnection', params= {"position": "next_1"})).json()
  
  if data['next_1']:
    #El nodo al que me quiero conectar ahora tiene como 'next_2' a su antiguo 'next_1'.
     requests.post('http://'+url+'/Insert', params= {"password": password, "url": data["next_1"], "position": "next_2"})

    #Mi segundo sguiente es el correspondiente del nodo al que me quiero conectar. 
     data['next_2'] = (requests.get('http://'+data['next_1']+'/GetConnection', params= {"position": "next_1"})).json()
  else:
    #Si data['next_1'] == '' implica que te conectaste a un nodo que estaba solo, por tanto, tu próximo es él.
    data['next_1'] = url

  #El nodo al que me quiero conectar ahora me tiene como su 'next_1'.
  requests.post('http://'+url+'/Insert', params= {"password": password, "url": data["me"], "position": "next_1"})

  #El nodo anterior al que me quiero conectar.
  url_prev = (requests.get('http://'+url+'/GetConnection', params= {"position": "previous"})).json()

  if url_prev:
    #El nado anterior al que me quiero conectar ahora me tiene a mi como segundo siguiente.
    
    requests.post('http://'+url_prev+'/Insert', params= {"password": password, "url": data['me'], "position": "next_2"})
  else:
    #Si no existe el anterior al nodo al que me quiero conectar, significa que es el primer nodo de la red, por tanto, su anterior soy yo.
    requests.post('http://'+url+'/Insert', params= {"password": password, "url": data['me'], "position": "previous"})

  #El nodo siguiente al que le pedí conexión ahora me tiene como su anterior.
  requests.post('http://'+ data['next_1'] + '/Insert', params= {"password": password, "url": data['me'], "position": "previous"})

  # Para guard el .json
  with open('./connections.json', 'w') as file:
    json.dump(data, file)   
     
  requests.post('http://'+ data['me'] + '/PostData')
  requests.post('http://'+ data['next_1'] + '/PostData', params={"clean" : True})
  
 
  return


@connection_servers.get("/GetData")
def get_data(inherited: bool):
  if not inherited:
    with open('./personal_data.json') as file_p:
      data = json.load(file_p)
  else:
    with open('./inherited_data.json') as file_h:
      data = json.load(file_h)
  aux = data
  if not inherited:
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data, file_p)
  else:   
    with open('./inherited_data.json', 'w') as file_h:
      json.dump(data, file_h)
  return aux


@connection_servers.post("/PostData")
def post_data(clean=False):
  with open('./inherited_data.json') as file_h:
    data_h = json.load(file_h)
  with open('./connections.json') as file:
    data = json.load(file)
  previous = data["previous"]
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  if clean:
    data_h = {"users": []}
  else:
    data_p = (requests.get('http://'+previous+'/GetData', params= {"inherited": False})).json()  
    for user in data_p["users"]:
      data_h["users"].append(user)
  with open('./inherited_data.json', 'w') as file_h:
    json.dump(data_h, file_h)
  return 


def disconnect(data):
  password = data['password']
    #Mi 'next_1' ahora es mi 'next_2'.
  data['next_1'] = data['next_2'] 
  if data["next_2"]:
    #Para desconectar a 'next_1' el anterior a mi 'next_2' ahora soy yo.
    requests.post('http://'+data["next_2"]+'/Insert', params= {"password": password, "url": data["me"], "position": "previous"})  
    #Mi 'next_2' será el 'next_1' de mi antiguo 'next_2'.
    data['next_2'] = (requests.get('http://'+data["next_2"]+'/GetConnection', params= {"position": "next_1"})).json()
    if data['next_2'] == data['me']:
      data['next_2'] = ""
  if data['previous'] and ping(data["previous"]) == 200:
    if data['previous'] == data['next_1']:
      #Actualizar el anterior a mi con su 'next_2' igual a mi nuevo 'next_1'.
      requests.post('http://'+data["previous"]+'/Insert', params= {"password": password,"url": "", "position": "next_2"}) 
    else:
      requests.post('http://'+data["previous"]+'/Insert', params= {"password": password,"url": data["next_1"], "position": "next_2"}) 

    inherited_data = (requests.get('http://'+data["next_1"]+'/GetData', params= {"inherited": True})).json()      
    requests.post('http://'+data["next_1"]+'/PostData') 
    with open('./personal_data.json') as file_p:
      data_p = json.load(file_p)
    for user in inherited_data["users"]:
      data_p["users"].append(user)
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data_p, file_p)    
  else:
    data['previous'] = ""
     
    with open('./personal_data.json') as file_p:
      data_p = json.load(file_p)
    with open('./inherited_data.json') as file_h:
      data_h = json.load(file_h)
    for user in data_h["users"]:
      data_p["users"].append(user)
    data_h = {"users":[]}
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data_p, file_p)
    with open('./inherited_data.json', 'w') as file_h:
      json.dump(data_h, file_h)


@connection_servers.get("/Ping")
def ping(server):    
  ip = server.split(":")[0] + ":8080"
  try:
    requests.get('http://'+ip+ "/Active", timeout=1.5)
    return 200
  except:
    return 500
    
        
@service.get("/Active")
def active():
  return True    


@connection_servers.get("/GetConnection")
def get_connection(position: str):
  with open('./connections.json') as file:
    data = json.load(file)
  aux = data[position]
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  return aux


@connection_servers.post("/Insert")
def insert(password: str, url: str, position: str):    
    with open('./connections.json') as file:
      data = json.load(file)
      if data['password'] == password:
        data[position] = url
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
  

@connection_servers.on_event('startup')
@repeat_every(seconds=3)
def check():
  with open('./connections.json') as file:
    data = json.load(file)
    if data["next_1"] and ping(data["next_1"]) != 200:
      disconnect(data)
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  

@connection_servers.get("/IsConnect")
def isconnect(url_to_search: str, who_asks):
  with open('./connections.json') as file:
    data = json.load(file)
  if url_to_search == data['me'] or url_to_search == data['next_1']:
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    return True
  elif who_asks == data['me'] or who_asks == data['next_1']:
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    return False
  next = data['next_2']
  with open('./connections.json', 'w') as file:
      json.dump(data, file)
  return (requests.get('http://'+next+'/IsConnect', params= {"url_to_search": url_to_search, "who_asks": who_asks})).json()


#buscar el servidor q tiene el personal data de este usuario
@connection_servers.get("/FindServer")
def findServer(user_nick: str, who_asks: str):
  with open('./personal_data.json') as file_p:
    personal_data = json.load(file_p)
  with open('./connections.json') as file:
    data = json.load(file)
  users = personal_data['users']
  for user in users:
    if user_nick == user['nickname']:
      with open('./connections.json', 'w') as file:
        json.dump(data, file)
      with open('./personal_data.json', 'w') as file_p:
        json.dump(personal_data, file_p)
      return data["me"]
  if not who_asks or who_asks == data['me']:
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    with open('./personal_data.json', 'w') as file_p:
      json.dump(personal_data, file_p)
    return None
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  with open('./personal_data.json', 'w') as file_p:
    json.dump(personal_data, file_p)
  return (requests.get('http://'+data['next_1']+'/FindServer', params= {"user_nick": user_nick, "who_asks": who_asks})).json()

@connection_servers.post("/SendMessage")  #Permite enviar un mensaje de desde "my_nickname" hacia "you_nickname".
def send_message(my_nickname: str, your_nickname: str, message: str, inherited: bool):
  if not inherited:
    with open('./personal_data.json') as file_p:
      data_p = json.load(file_p)      
    for i in data_p['users']:
      if my_nickname == i['nickname']:
        if not i["contacts"].__contains__(your_nickname):
          i["contacts"][your_nickname] = "Unknown"
        if i['messages'].__contains__(your_nickname):
          i['messages'][your_nickname].append(['you', message])
        else:
          i['messages'][your_nickname] = [['you', message]]
      elif your_nickname == i['nickname']:
        if not i["contacts"].__contains__(my_nickname):
          i["contacts"][my_nickname] = "Unknown"
        if i['messages'].__contains__(my_nickname):
          i['messages'][my_nickname].append([my_nickname, message])
        else:
          i['messages'][my_nickname] = [[my_nickname, message]]  
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data_p, file_p)
    with open('./connections.json') as file:
      data = json.load(file)
    next_1 = data["next_1"]
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    if next_1 and ping(next_1) == 200:
      requests.post('http://'+next_1+'/SendMessage', params= {"my_nickname": my_nickname, "your_nickname": your_nickname, "message": message, "inherited": True})
    
  else:  
    with open('./inherited_data.json') as file_p:
      data_h = json.load(file_p)      
    for i in data_h['users']:
      if my_nickname == i['nickname']:
        if not i["contacts"].__contains__(your_nickname):
          i["contacts"][your_nickname] = "Unknown"
        if i['messages'].__contains__(your_nickname):
          i['messages'][your_nickname].append(['you', message])
        else:
          i['messages'][your_nickname] = [['you', message]]
      elif your_nickname == i['nickname']:
        if not i["contacts"].__contains__(my_nickname):
          i["contacts"][my_nickname] = "Unknown"
        if i['messages'].__contains__(my_nickname):
          i['messages'][my_nickname].append([my_nickname, message])
        else:
          i['messages'][my_nickname] = [[my_nickname, message]]  
      with open('./inherited_data.json', 'w') as file_h:
        json.dump(data_h, file_h)
  return 


@connection_servers.get("/CheckPassword")
def check_password(nickname: str, password: str):
  with open('./personal_data.json') as file_p:
    personal_data = json.load(file_p)
  for user in personal_data["users"]:
    if user["nickname"] == nickname:
      if user["password"] == password:
        with open('./personal_data.json', 'w') as file_p:
          json.dump(personal_data, file_p)
        return True
      else:
        break
  with open('./personal_data.json', 'w') as file_p:
    json.dump(personal_data, file_p)
  return False


@connection_servers.get("/DiscoverNext")
def discover_next():
  with open('./connections.json') as file:
    data = json.load(file)
  aux = data["next_1"]
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  return aux


@connection_servers.get("/GetMessages")
def get_messages(my_nickname: str, your_nickname: str):
  with open('./personal_data.json') as file_p:
    data = json.load(file_p)
  for user in data["users"]:
    if user["nickname"] == my_nickname:
      contact_name = user["contacts"][your_nickname] 
      if contact_name == "Unknown":
         contact_name = your_nickname
      aux = user["messages"][your_nickname] if user["messages"].__contains__(your_nickname) else []
      for message in aux:
        if message[0] == your_nickname:
          message[0] = contact_name
  with open('./personal_data.json', "w") as file_p:
    json.dump(data, file_p)
  return aux


@connection_servers.post("/AddContact")
def add_contact(my_nickname: str, contact_name: str, your_nickname: str, inherited=False):
  if not inherited:
    with open('./personal_data.json') as file_p:
      data = json.load(file_p)
  else:
    with open('./inherited_data.json') as file_h:
      data = json.load(file_h)
  for user in data["users"]:
    if user["nickname"] == my_nickname: 
        user["contacts"][your_nickname] = contact_name
        break
  if not inherited:  
    with open('./personal_data.json', "w") as file_p:
      json.dump(data, file_p)
    with open('./connections.json') as file:
      data = json.load(file)
    if data["next_1"] and ping(data["next_1"]) == 200:
      requests.post('http://'+data["next_1"]+'/AddContact', params= {"my_nickname": my_nickname, "contact_name": contact_name, "your_nickname": your_nickname, "inherited": True})
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
  else:
    with open('./inherited_data.json', "w") as file_h:
      json.dump(data, file_h)
  return 


@connection_servers.get("/Contacts")
def contacts(nickname: str):
  with open('./personal_data.json') as file_p:
    data = json.load(file_p)
  for user in data["users"]:
    if user["nickname"] == nickname:
      with open('./personal_data.json', "w") as file_p:
        json.dump(data, file_p)
      return user["contacts"]

