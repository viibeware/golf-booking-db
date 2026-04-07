FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir flask reportlab

COPY . .

RUN mkdir -p /data

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

EXPOSE 5000

CMD ["python", "app.py"]
