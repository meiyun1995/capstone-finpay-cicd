FROM python:3.12-alpine@sha256:e6dae589c1c05976188fd3bd019afd091445fc533ed2ea29001beddc7368a9c8
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app.py transaction.py ./

RUN addgroup -S -g 10001 appuser \
    && adduser -S -D -H -u 10001 -G appuser \
       -s /sbin/nologin appuser

USER appuser

EXPOSE 8000

CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]