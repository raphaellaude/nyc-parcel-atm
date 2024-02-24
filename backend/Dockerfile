ARG PYTHON_VERSION=3.12.2-slim-bullseye
FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED True
ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

RUN pip install poetry --no-cache-dir
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-root --no-interaction

RUN apt-get update && \
    apt-get install -y openssh-client

CMD ["poetry", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
