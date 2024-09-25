FROM python:3.9

RUN pip install --upgrade pip

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt --no-cache-dir

COPY . .

COPY entrypoint.sh /app/entrypoint.sh

ENTRYPOINT [ "sh", "/app/entrypoint.sh" ]