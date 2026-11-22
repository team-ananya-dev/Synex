# API image for Render (free plan). Mailpit runs inside the same container as the local inbox:
# a free Render service has one public port, and the inbox must never be public.
FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates && rm -rf /var/lib/apt/lists/*

# Mailpit v1.34.0 (MIT, github.com/axllent/mailpit), checked against the release's published SHA-256
RUN curl -fsSL -o /tmp/mailpit.tgz https://github.com/axllent/mailpit/releases/download/v1.34.0/mailpit-linux-amd64.tar.gz \
 && echo "af236b42f171b1c74f0ac5ff444f44d36f2f2ecc0134f5a2f1d4e307e56a0d2c  /tmp/mailpit.tgz" | sha256sum -c - \
 && tar -xzf /tmp/mailpit.tgz -C /usr/local/bin mailpit && rm /tmp/mailpit.tgz

WORKDIR /app/server
COPY server/requirements.txt ./requirements.txt
COPY server/requirements ./requirements
RUN pip install --no-cache-dir -r requirements.txt

COPY server /app/server
COPY deploy/start-api.sh /app/start-api.sh
RUN chmod +x /app/start-api.sh && mkdir -p /app/data

# demo mode: no dev cache, no dev result limits
ENV SYNEX_DEMO=1 SYNEX_DB=/app/data/synex.db SYNEX_SMTP_HOST=127.0.0.1 SYNEX_SMTP_PORT=1025 SYNEX_MAILPIT_API=http://127.0.0.1:8025
CMD ["/app/start-api.sh"]
