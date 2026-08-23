FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY data /app/data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app.api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
