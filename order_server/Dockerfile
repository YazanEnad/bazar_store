FROM python:3.12-slim

WORKDIR /app

COPY order_server/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY order_server/ ./order_server/

EXPOSE 5002

CMD ["python", "order_server/order_server.py"]