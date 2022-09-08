FROM python:3.10-alpine as builder-image
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
RUN apk update && apk add postgresql-dev gcc python3-dev \
    musl-dev libffi-dev libevent-dev libart-lgpl zlib-dev \
    libxslt-dev zlib libc-dev linux-headers freetype-dev pgbouncer
RUN pip install --upgrade pip
WORKDIR /usr/src/app
COPY ./requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /usr/src/app/wheels -r requirements.txt


FROM python:3.10-alpine
WORKDIR /app
RUN apk update && apk add freetype-dev libpq pgbouncer
COPY --from=builder-image /usr/src/app/wheels /wheels
COPY --from=builder-image /usr/src/app/requirements.txt .
RUN pip install --no-cache /wheels/*
COPY . .
RUN chmod +x ./compile
RUN ls -l
RUN ./compile /app
RUN python manage.py collectstatic --noinput