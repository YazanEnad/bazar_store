FROM python:3.12-slim

WORKDIR /app

COPY frontend_server/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY frontend_server/ ./frontend_server/

EXPOSE 5000

CMD ["python", "frontend_server/frontend_server.py"]