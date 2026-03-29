FROM python:3.11-slim

# gcc + libc6-dev + python3-dev required to compile pyswisseph C extension.
# wget + ca-certificates for reliable HTTPS downloads.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    python3-dev \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Swiss Ephemeris data files (high precision)
# Try astro.com first; if unavailable on HF network, use fallback mirror.
RUN set -eux; \
    mkdir -p /app/ephe; \
    wget --https-only --tries=5 --waitretry=2 --retry-connrefused \
      -O /app/ephe/sepl_18.se1 \
      https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1 \
    || wget --https-only --tries=5 --waitretry=2 --retry-connrefused \
      -O /app/ephe/sepl_18.se1 \
      https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/sepl_18.se1; \
    wget --https-only --tries=5 --waitretry=2 --retry-connrefused \
      -O /app/ephe/semo_18.se1 \
      https://www.astro.com/ftp/swisseph/ephe/semo_18.se1 \
    || wget --https-only --tries=5 --waitretry=2 --retry-connrefused \
      -O /app/ephe/semo_18.se1 \
      https://raw.githubusercontent.com/aloistr/swisseph/master/ephe/semo_18.se1; \
    test -s /app/ephe/sepl_18.se1; \
    test -s /app/ephe/semo_18.se1; \
    ls -lh /app/ephe

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860
ENV OPENAI_API_KEY=""

# Optional but recommended if your app sets swe.set_ephe_path:
# ENV SE_EPHE_PATH="/app/ephe"

CMD ["python", "app.py"]
