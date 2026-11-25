FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

<<<<<<< Updated upstream
# Primero las dependencias (aprovecha la caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Luego el código del proyecto
=======

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


>>>>>>> Stashed changes
COPY . .

EXPOSE 8000

<<<<<<< Updated upstream
# Crea las tablas y arranca el servidor de desarrollo
CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
=======

CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"]
>>>>>>> Stashed changes
