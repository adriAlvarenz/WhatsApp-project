import uvicorn


if __name__ == "__main__":
    print("Host: ")
    host = input()
    uvicorn.run("user:server_interface", host=host, port=9000, reload=True)


