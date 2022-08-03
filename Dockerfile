FROM python:3.8

RUN mkdir /app
RUN mkdir /certs

WORKDIR /app
COPY . /app/

RUN mkdir tmpfs

RUN python3 -m venv /env
RUN . /env/bin/activate
RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt


CMD gunicorn --workers 4 --max-requests 1000 \
    --timeout 240 --bind :80 --capture-output \
    --error-logfile - --log-file - \
    --worker-tmp-dir ./tmpfs/  app:app
