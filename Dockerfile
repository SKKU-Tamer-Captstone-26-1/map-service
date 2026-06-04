FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV MAP_SERVICE_API_HOST=0.0.0.0
ENV MAP_SERVICE_API_PORT=8080
ENV MAP_SERVICE_API_LOGS=false

EXPOSE 8080

CMD ["python", "-m", "scripts.api.map_read_api", "--host", "0.0.0.0", "--port", "8080"]
