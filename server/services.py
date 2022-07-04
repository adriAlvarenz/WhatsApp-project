import uvicorn

#levanta el servicio que se utiliza para el ping
if __name__ == "__main__":
    print("Host: ")
    host = input()
    uvicorn.run("server:service", host=host, port=8080, reload=True)