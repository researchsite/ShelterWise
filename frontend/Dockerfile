FROM python:3.11-alpine

WORKDIR /app
COPY . /app

ENV PORT=8080 \
    ADK_BACKEND_URL="https://shelterwise-backend-335751565476.us-central1.run.app" \
    ADK_APP_NAME="shelterwise_agent"

EXPOSE 8080

CMD ["python3", "server.py"]
