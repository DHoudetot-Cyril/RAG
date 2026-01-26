FROM pytorch/pytorch:2.2.0-cuda12.1-cudnn8-runtime

WORKDIR /app

# Install system dependencies for Docling
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpoppler-cpp-dev \
    poppler-utils \
    tesseract-ocr \
    libtesseract-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
COPY requirements.txt .
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
