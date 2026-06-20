FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api/requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8790

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8790"]
