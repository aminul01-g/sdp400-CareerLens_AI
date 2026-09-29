FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --upgrade pip && pip install -r requirements.txt
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:8000", "--workers", "2"]
