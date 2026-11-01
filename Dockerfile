FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .

RUN python -m pip install --no-cache-dir -r requirements.txt

COPY app.py transaction.py ./

RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --no-create-home \
       --shell /usr/sbin/nologin appuser

USER appuser

EXPOSE 8000

CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "app:app"]