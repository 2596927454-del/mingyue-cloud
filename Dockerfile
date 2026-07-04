FROM python:3.12-slim

WORKDIR /app

COPY project/phase2/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -q

COPY project/phase2/app.py .

ENV FLASK_HOST=0.0.0.0

CMD ["python", "app.py"]
