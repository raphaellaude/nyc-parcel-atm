# Frontend
FROM node:18
WORKDIR /app
COPY pluto-hist/package.json .
RUN npm install
COPY pluto-hist/ .
RUN npm run build
EXPOSE 8080
CMD [ "npm", "run", "preview" ]

# Backend
FROM python:3.12.1

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV GDAL_LIBRARY_PATH /usr/lib/ogdi/4.1/libgdal.so

RUN apt-get update \
    && apt-get install -y binutils libproj-dev gdal-bin python3-gdal libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip
RUN pip install poetry

WORKDIR /app
COPY backend/pyproject.toml backend/poetry.lock* ./
RUN poetry config virtualenvs.create false
RUN poetry install

COPY backend/ .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
