FROM python:3.11-slim

# gcc + libc6-dev + python3-dev are required to compile the
# pyswisseph C extension from source during pip install.
# Do NOT use Alpine — musl libc breaks the compilation.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Gradio default port — auto-mapped by Hugging Face Spaces
EXPOSE 7860

# Set at runtime via HF Spaces Secrets or Railway Variables
ENV OPENAI_API_KEY=""

CMD ["python", "app.py"]
