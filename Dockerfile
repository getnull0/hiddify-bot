FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY . .

RUN useradd -m -u 1000 botuser
USER botuser

CMD ["python", "bot.py"]
