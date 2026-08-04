FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY run.sh ./run.sh
RUN chmod +x /app/run.sh && sed -i 's/\r$//' /app/run.sh

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8099

CMD ["bash", "/app/run.sh"]
