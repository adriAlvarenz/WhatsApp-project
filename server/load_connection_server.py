import uvicorn
import json
import os

#Este codigo es para cargar el servidor

#Se recibe el ip del servidor y el puerto
#Password debe ser la misma del servidor al que uno se quiera conectar
if __name__ == "__main__":
    print('Host: ')
    host = input()
    print('Port: ')
    port = input()
    print('Password: ')
    password = input()

#Se prepara la tabla de conexion
    data = {}
    data['seconds'] = ""
    data['password'] = password    
    data['me'] = host + ':' + port
    data['previous'] = ""
    data['next_1'] = ""
    data['next_2'] = ""
    # Para guard el .json
    with open('./connections.json', 'w') as file:
        json.dump(data, file)

#Se preparan los archivos de almacenamiento de informacion.
    data = {}
    data["users"] = []
    with open('./personal_data.json', 'w') as file_p:
        json.dump(data, file_p)    
    with open('./inherited_data.json', 'w') as file_h:
        json.dump(data, file_h)

#Se corre el servidor
    uvicorn.run("server:connection_servers", host=host, port=int(port), reload=True)    
    

