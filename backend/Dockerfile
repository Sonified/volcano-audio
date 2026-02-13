FROM python:3.11.11-slim

WORKDIR /app

# Install system dependencies needed by ObsPy/scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    gfortran \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify setuptools/pkg_resources is available
RUN python -c "import pkg_resources; print('pkg_resources OK')"

# Copy application code
COPY . .

# Railway sets PORT env var
CMD ["python", "collector_loop.py"]
