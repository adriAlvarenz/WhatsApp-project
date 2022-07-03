import uvicorn


if __name__ == "__main__":
    print("Host: ")
    host = input()
    uvicorn.run("server:service", host=host, port=8080, reload=True)