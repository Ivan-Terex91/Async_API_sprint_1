FROM python:3.9-slim
EXPOSE 8000
WORKDIR /api/app

RUN apt-get update && apt-get upgrade

COPY . /api

RUN pip install -r /api/requirements/prod.txt --no-cache-dir

CMD ["sleep", "infinity"]
