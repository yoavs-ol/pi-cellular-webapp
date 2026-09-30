FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    modemmanager \
    libqmi-utils \
    python3-serial \
    sqlite3 \
    iproute2 \
    iputils-ping \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

RUN mkdir -p /var/lib/cellular-config /var/lib/cellular-captures

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "-w", "2", "--timeout", "120", "app.main:app"]
