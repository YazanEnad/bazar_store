FROM python:3.12-slim

WORKDIR /app

COPY catalog_server/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY catalog_server/ ./catalog_server/

EXPOSE 5001

CMD ["python", "catalog_server/catalog_server.py"]