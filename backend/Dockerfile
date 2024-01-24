ARG PYTHON_VERSION=3.12.1

FROM python:${PYTHON_VERSION}

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install psycopg2 dependencies.
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    binutils \
    libproj-dev \
    gdal-bin \
    python3-gdal \
    libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /code

WORKDIR /code

RUN pip install poetry
COPY pyproject.toml poetry.lock /code/
RUN poetry config virtualenvs.create false
RUN poetry install --only main --no-root --no-interaction
COPY . /code

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8000", "--workers", "2", "pluto_hist.wsgi"]
