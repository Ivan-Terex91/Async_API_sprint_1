FROM python:3.9-slim
EXPOSE 8000
WORKDIR /api/app

RUN apt-get update && apt-get --yes upgrade

COPY ./requirements /api/requirements
RUN pip install -r /api/requirements/prod.txt --no-cache-dir

COPY . /api

CMD ["sleep", "infinity"]
