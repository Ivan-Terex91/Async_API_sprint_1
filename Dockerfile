FROM python:3.9-alpine
EXPOSE 8000
WORKDIR /app

RUN \
    apk add --no-cache postgresql-libs && \
    apk add --no-cache --virtual .build-deps gcc musl-dev postgresql-dev postgresql-libs

COPY requirements /app/requirements

RUN \
    pip install -r requirements/dev.txt --no-cache-dir && \
    apk --purge del .build-deps

CMD ["sleep", "infinity"]
