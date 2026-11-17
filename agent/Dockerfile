FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PORT=8080 \
    PROJECT_ID=qwiklabs-gcp-04-99fa355171e1 \
    BIGQUERY_DATASET=a4i_housing \
    METRO_AREA="San Francisco" \
    PYTHONPATH="/app"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["python", "server.py"]
