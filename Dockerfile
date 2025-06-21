FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      curl cron logrotate && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/generated_files /var/log/tts && \
    chown root:root /var/log/tts

COPY logrotate-tts /etc/logrotate.d/tts
RUN chmod 644 /etc/logrotate.d/tts

RUN mkdir -p /app/voices && \
    curl -L https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx \
      -o /app/voices/de_DE-thorsten-high.onnx && \
    curl -L https://huggingface.co/Thorsten-Voice/Piper/resolve/main/de_DE-thorsten-high.onnx.json \
      -o /app/voices/de_DE-thorsten-high.onnx.json

RUN echo "0 0 * * * root /usr/sbin/logrotate /etc/logrotate.d/tts" \
      > /etc/cron.d/logrotatetts && \
    chmod 644 /etc/cron.d/logrotatetts

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000
CMD ["/entrypoint.sh"]
                                                                                                                    5,1        Anfang
