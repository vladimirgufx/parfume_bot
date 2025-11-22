FROM python:3.9-slim

WORKDIR /app        # ← ЭТО НУЖНО ОСТАВИТЬ!

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
