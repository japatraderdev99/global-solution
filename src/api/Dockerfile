# API Sentinela Orbital — container para Cloud Run.
# Sem dependencias externas (biblioteca padrao do Python).
FROM python:3.12-slim

WORKDIR /app
COPY mock_server.py ./

# Cloud Run injeta a porta via $PORT (default 8080).
ENV PORT=8080
EXPOSE 8080

CMD ["python", "mock_server.py"]
