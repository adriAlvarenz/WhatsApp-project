from fastapi import FastAPI
import json
import requests 
from fastapi_utils.tasks import repeat_every
from sqlalchemy import false, true
from urllib3 import Retry

service = FastAPI(docs_url=None)

connection_servers = FastAPI()  #Conexión entre los servidores.

#Para registrar un usuario: escribir su informacion en donde corresponda.
@connection_servers.post("/RegisterUser")
def register_user(name: str, nickname: str, password: str, inherited=False):
  with open('./connections.json') as file:
      data = json.load(file)
  #se busca por los servidores para saber si el usuario ya esta registrado
  check = (requests.get('http://'+data["me"]+'/FindServer', params= {"user_nick": nickname, "who_asks": data["previous"]})).json()
  with open('./connections.json', 'w') as file:
      json.dump(data, file)
  if not inherited and check:
    return "You are already registered"
  #se carga el archivo que corresponda, en dependencia si es informacion propia o replicada
  if not inherited:
    with open('./personal_data.json') as file_p:
      data = json.load(file_p)
  else:
    with open('./inherited_data.json') as file_h:
      data = json.load(file_h)      
  #se añade la información del usuario al servidor
  data['users'].append({
    'name': name, 
    'nickname': nickname,
    'password': password,
    'contacts': {},
    'messages':{}})
  if not inherited:
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data, file_p)   
  #si es informacion propia es necesario mandar a replicarla
    with open('./connections.json') as file:
      data = json.load(file)
  #se verifica si hay a quien mandar a replicar y en caso afirmativo se hace
    if data["next_1"] and ping(data["next_1"]) == 200:
      requests.post('http://'+data["next_1"]+'/RegisterUser', params= {"name": name, "nickname": nickname, "password": password, "inherited": True})
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
  else:
    with open('./inherited_data.json', 'w') as file_h:
      json.dump(data, file_h)
  return

#conectar un servidor a otro
@connection_servers.post("/Connect")
def connect(url: str):
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
  
  with open('./connections.json', 'w') as file:
    json.dump(data, file)   
  
  #voy a replicar el data propio de mi antecesor
  requests.post('http://'+ data['me'] + '/PostData')

  #mi sucesor va a replicar mi información, la cual es necesariamente vacia y por ende se manda a limpiar su data replicado
  requests.post('http://'+ data['next_1'] + '/PostData', params={"clean":true})
  

  return

#para obtener el data propio o replicado en dependencia del parámetro
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

#Replicar información
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
  #se limpia la información replicada que guarda este servidor
    data_h = {"users": []}
  else:
    #se obtiene el data propio de mi antecesor, el cual debo replicar en mi
    data_p = (requests.get('http://'+previous+'/GetData', params= {"inherited": False})).json()  
    #se añade a mi información replicada la información propia de mi antecesor
    for user in data_p["users"]:
      data_h["users"].append(user)
  with open('./inherited_data.json', 'w') as file_h:
    json.dump(data_h, file_h)
  return 


#se desconecta mi nodo sucesor
def disconnect(data):
  password = data['password']
    #Mi 'next_1' ahora es mi 'next_2'.
  data['next_1'] = data['next_2'] 
  if data["next_2"]:
    #Para desconectar a 'next_1' el anterior a mi 'next_2' ahora soy yo.
    requests.post('http://'+data["next_2"]+'/Insert', params= {"password": password, "url": data["me"], "position": "previous"})  
    #Mi 'next_2' será el 'next_1' de mi antiguo 'next_2'.
    data['next_2'] = (requests.get('http://'+data["next_2"]+'/GetConnection', params= {"position": "next_1"})).json()
    #caso especial: si eramos 3 servidores y ahora somos 2 tengo que limpiar mi segundo predecesor
    if data['next_2'] == data['me']:
      data['next_2'] = ""
  
  if data['previous'] and ping(data["previous"]) == 200:
    if data['previous'] == data['next_1']:
      #solo quedamos 2, actualizar el otro nodo limpiando su next2
      requests.post('http://'+data["previous"]+'/Insert', params= {"password": password,"url": "", "position": "next_2"}) 
    else:
      #Actualizar el anterior a mi con su 'next_2' igual a mi nuevo 'next_1'.
      requests.post('http://'+data["previous"]+'/Insert', params= {"password": password,"url": data["next_1"], "position": "next_2"}) 

    #me quedo con el data replicado de mi sucesor
    inherited_data = (requests.get('http://'+data["next_1"]+'/GetData', params= {"inherited": True})).json()      
    #mi sucesor añade mi data propio a su data replicado
    requests.post('http://'+data["next_1"]+'/PostData') 
    with open('./personal_data.json') as file_p:
      data_p = json.load(file_p)
    #añado a mi data propio el data replicado que tiene mi sucesor y yo no tengo 
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


#llama a un endpoint dentro del server que quiero comprobar su conexión
@connection_servers.get("/Ping")
def ping(server):    
  ip = server.split(":")[0] + ":8080"
  try:
    requests.get('http://'+ip+ "/Active", timeout=1.5)
    return 200
  except:
    return 500

#endpoint para verificar conexión         
@service.get("/Active")
def active():
  return True    

#para ver la tabla de conexión de otro servidor, el parámetro puede ser previous, next1 o next2
@connection_servers.get("/GetConnection")
def get_connection(position: str):
  with open('./connections.json') as file:
    data = json.load(file)
  aux = data[position]
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  return aux

#para cambiar la tabla de conexiones de otro servidor
@connection_servers.post("/Insert")
def insert(password: str, url: str, position: str):    
    with open('./connections.json') as file:
      data = json.load(file)
      #solo puedes editarme si tu contraseña es igual a la mía
      if data['password'] == password:
        data[position] = url
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
  
#para chequear periódicamente la conexión de los servidores
@connection_servers.on_event('startup')
@repeat_every(seconds=3)
def check():
  with open('./connections.json') as file:
    data = json.load(file)
    #si no puedo llegar a mi next1 desconectalo de la red
    if data["next_1"] and ping(data["next_1"]) != 200:
      disconnect(data)
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  
#verificar si un servidor específico está conectado
@connection_servers.get("/IsConnect")
def isconnect(url_to_search: str, who_asks):
  with open('./connections.json') as file:
    data = json.load(file)
  #si me buscan a mí o a mi sucesor digo que sí
  if url_to_search == data['me'] or url_to_search == data['next_1']:
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    return True
  #si yo o mi sucesor somos los que preguntamos, digo que no
  elif who_asks == data['me'] or who_asks == data['next_1']:
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    return False
  #me muevo a mi next2
  next = data['next_2']
  with open('./connections.json', 'w') as file:
      json.dump(data, file)
  #me busco en el endpoint de este método en mi next2
  return (requests.get('http://'+next+'/IsConnect', params= {"url_to_search": url_to_search, "who_asks": who_asks})).json()


#buscar el servidor q tiene el personal data de este usuario
@connection_servers.get("/FindServer")
def findServer(user_nick: str, who_asks: str):
  with open('./personal_data.json') as file_p:
    personal_data = json.load(file_p)
  with open('./connections.json') as file:
    data = json.load(file)
  users = personal_data['users']
  #revisar si algun usuario de los registrados en este servidor es el que busco
  for user in users:
    if user_nick == user['nickname']:
      #si lo encuentro cierro los json y lo devuelvo
      with open('./connections.json', 'w') as file:
        json.dump(data, file)
      with open('./personal_data.json', 'w') as file_p:
        json.dump(personal_data, file_p)
      return data["me"]
  #si vuelvo a la persona que pregunta devuelvo None 
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
  #sigo buscando preguntándole a mi sucesor
  return (requests.get('http://'+data['next_1']+'/FindServer', params= {"user_nick": user_nick, "who_asks": who_asks})).json()


#Permite enviar un mensaje de desde "my_nickname" hacia "you_nickname".
@connection_servers.post("/SendMessage")  
def send_message(my_nickname: str, your_nickname: str, message: str, inherited: bool):
  if not inherited:
    with open('./personal_data.json') as file_p:
      data_p = json.load(file_p)    
    #se buscan los usuarios involucrados en el mensaje  
    for i in data_p['users']:
      #me encuentran a mí
      if my_nickname == i['nickname']:
        #si la persona que me mando el mensaje no está en mis contactos registro su nickname público con nombre desconocido
        if not i["contacts"].__contains__(your_nickname):
          i["contacts"][your_nickname] = "Unknown"
        #si ya existen mensajes con esta persona se agrega el nuevo
        if i['messages'].__contains__(your_nickname):
          i['messages'][your_nickname].append(['you', message])
        #si no existen mensajes previos con esta persona se crea el 'chat' con ella
        else:
          i['messages'][your_nickname] = [['you', message]]
      #encuentran a la otra persona
      elif your_nickname == i['nickname']:
        #si no estoy en sus contactos me agrega con mi nick público y con nombre desconocido
        if not i["contacts"].__contains__(my_nickname):
          i["contacts"][my_nickname] = "Unknown"
        #si ya existen mensajes entre nosotros lo agrega a estos
        if i['messages'].__contains__(my_nickname):
          i['messages'][my_nickname].append([my_nickname, message])
        #si es el primer mensaje entre nosotros crea el 'chat'
        else:
          i['messages'][my_nickname] = [[my_nickname, message]]  
    with open('./personal_data.json', 'w') as file_p:
      json.dump(data_p, file_p)
    with open('./connections.json') as file:
      data = json.load(file)
    next_1 = data["next_1"]
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
    #verifico si el servidor que sucede a este está conectado y lo mando a replicar la información que ya se guardó en este
    if next_1 and ping(next_1) == 200:
      requests.post('http://'+next_1+'/SendMessage', params= {"my_nickname": my_nickname, "your_nickname": your_nickname, "message": message, "inherited": True})
  #esta cláusula hace lo mismo que su correspondiente 'if' sin replicar, solo se entra en la replica. 
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


#verifica que la contraseña ingresada para loggearse es correcta
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


#devuelve el sucesor del servidor 
@connection_servers.get("/DiscoverNext")
def discover_next():
  with open('./connections.json') as file:
    data = json.load(file)
  aux = data["next_1"]
  with open('./connections.json', 'w') as file:
    json.dump(data, file)
  return aux


#devuelve los mensajes entre un par de usuarios
@connection_servers.get("/GetMessages")
def get_messages(my_nickname: str, your_nickname: str):
  with open('./personal_data.json') as file_p:
    data = json.load(file_p)
  #busco mi nombre en el data
  for user in data["users"]:
    if user["nickname"] == my_nickname:
      #me quedo con el nombre de contacto de la otra persona
      contact_name = user["contacts"][your_nickname] 
      #si su nombre de contacto es desconocido muestro su nickname en cambio
      if contact_name == "Unknown":
         contact_name = your_nickname
      #si tengo mensajes con esa persona los devuelvo, en su defecto muestro una lista vacía
      aux = user["messages"][your_nickname] if user["messages"].__contains__(your_nickname) else []
      #en caso de tener un nombre en el contacto se sustituye por el nickname a la hora de mostrar el chat
      for message in aux:
        if message[0] == your_nickname:
          message[0] = contact_name
  with open('./personal_data.json', "w") as file_p:
    json.dump(data, file_p)
  return aux


#añadir un nuevo contacto a mis contactos. También editar y eliminar.
@connection_servers.post("/AddContact")
def add_contact(my_nickname: str, contact_name: str, your_nickname: str, inherited=False):
  #en dependencia de si el data es propio o replica se abre el json que corresponda
  if not inherited:
    with open('./personal_data.json') as file_p:
      data = json.load(file_p)
  else:
    with open('./inherited_data.json') as file_h:
      data = json.load(file_h)
  #me encuentro entre los usuarios registrados en este servidor
  for user in data["users"]:
    if user["nickname"] == my_nickname: 
        #si no tengo el contacto lo creo, si lo tengo lo edito. Eliminar es editar con contactName Unknown
        user["contacts"][your_nickname] = contact_name
        break
  #se cierra el json que corresponda
  if not inherited:  
    with open('./personal_data.json', "w") as file_p:
      json.dump(data, file_p)
    with open('./connections.json') as file:
      data = json.load(file)
      #si estoy escribiendo en el servidor del data propio verifico que mi sucesor esté y lo mando a replicar
    if data["next_1"] and ping(data["next_1"]) == 200:
      requests.post('http://'+data["next_1"]+'/AddContact', params= {"my_nickname": my_nickname, "contact_name": contact_name, "your_nickname": your_nickname, "inherited": True})
    with open('./connections.json', 'w') as file:
      json.dump(data, file)
  else:
    with open('./inherited_data.json', "w") as file_h:
      json.dump(data, file_h)
  return 


#devuelve la lista de contactos de un usuario
@connection_servers.get("/Contacts")
def contacts(nickname: str):
  with open('./personal_data.json') as file_p:
    data = json.load(file_p)
  for user in data["users"]:
    if user["nickname"] == nickname:
      with open('./personal_data.json', "w") as file_p:
        json.dump(data, file_p)
      return user["contacts"]

