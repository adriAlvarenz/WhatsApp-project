FROM python:3.9
COPY ./requeriments.txt /requeriments.txt
COPY ./main.py main.py
COPY ./server.py /server.py
RUN pip install --no-cache-dir --upgrade -r /requirements.txt
CMD ["python3" "main.py"]  
