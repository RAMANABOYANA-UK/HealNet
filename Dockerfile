FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

ENV HEALNET_TRANSPORT=http
ENV HEALNET_HOST=0.0.0.0
ENV HEALNET_PORT=9000

EXPOSE 9000

CMD ["python", "-m", "healnet.server"]
