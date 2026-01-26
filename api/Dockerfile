FROM nvidia/cuda:12.1-runtime-ubuntu22.04

WORKDIR /app

# Install Python and system dependencies for Docling
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3-pip \
    python3.11-venv \
    curl \
    build-essential \
    libpoppler-cpp-dev \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -s /usr/bin/python3.11 /usr/bin/python

# Install Python packages
COPY requirements.txt .

# Install torch with CUDA support first
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cu121

# Install other packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["python", "main.py"]
