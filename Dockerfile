FROM python:3.8

RUN mkdir /app
WORKDIR /app
COPY . /app/

RUN mkdir tmpfs

RUN python3 -m venv /env
RUN . /env/bin/activate
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

EXPOSE 80

CMD gunicorn --workers 4 --max-requests 1000 \
    --timeout 240 --bind :80 \
    --certfile /home/ubuntu/certs/fullchain.pem \
    --keyfile /home/ubuntu/certs/privkey.pem \
    --error-logfile - --log-file - --log-level info \
    --worker-tmp-dir ./tmpfs/  app:app
