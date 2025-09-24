FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN apt-get update && apt-get install -y \
    gcc \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y gcc \
    && rm -rf /var/lib/apt/lists/*

COPY . .

ENV PYTHONPATH=/app

EXPOSE 10002

CMD ["gunicorn", "--bind", "0.0.0.0:10002", "app:app"]