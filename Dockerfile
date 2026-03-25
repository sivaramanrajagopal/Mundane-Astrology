FROM python:3.11-slim

# gcc + libc6-dev + python3-dev required to compile pyswisseph C extension.
# wget required to download Swiss Ephemeris data files.
# Do NOT use Alpine — musl libc breaks the C extension compilation.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    python3-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Swiss Ephemeris data files ────────────────────────────────────────────────
# sepl_18.se1 → planets (Sun–Saturn) accurate to <1 arcsec for 1800–2400 AD
# semo_18.se1 → Moon (critical for Nakshatra / Vimshottari Dasha calculation)
# Without these files pyswisseph silently falls back to low-precision Moshier,
# producing wrong Moon nakshatras and therefore wrong Dasha lords.
RUN mkdir -p /app/ephe && \
    wget -q -O /app/ephe/sepl_18.se1 \
         https://www.astro.com/ftp/swisseph/ephe/sepl_18.se1 && \
    wget -q -O /app/ephe/semo_18.se1 \
         https://www.astro.com/ftp/swisseph/ephe/semo_18.se1

# Install dependencies first (layer caching — runs before COPY . so ephe layer is stable)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Gradio default port — auto-mapped by Hugging Face Spaces
EXPOSE 7860

# Set at runtime via HF Spaces Secrets or Railway Variables
ENV OPENAI_API_KEY=""

CMD ["python", "app.py"]
