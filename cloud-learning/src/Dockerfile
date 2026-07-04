FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -q

COPY app.py .

ENV FLASK_HOST=0.0.0.0

CMD ["python", "app.py"]
