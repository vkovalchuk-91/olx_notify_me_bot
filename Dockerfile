FROM python:3.12-slim

WORKDIR /bot

COPY . /bot

RUN pip install --upgrade pip && \
    pip install -r requirements.txt --no-cache-dir

CMD ["python", "main.py"]
