FROM python:3.11-alpine

WORKDIR /app
RUN pip install --no-cache-dir requests
COPY . /app

ENV PORT=8080 \
    ADK_BACKEND_URL="https://shelterwise-backend-335751565476.us-central1.run.app" \
    ADK_APP_NAME="shelterwise"

EXPOSE 8080

CMD ["python3", "server.py"]
