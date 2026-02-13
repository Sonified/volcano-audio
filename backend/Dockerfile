FROM python:3.11.11-slim

WORKDIR /app

# Install system dependencies needed by ObsPy/scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    gfortran \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Install setuptools 69.x (last version that includes pkg_resources)
# DO NOT upgrade past 69.x — setuptools 80+ removed pkg_resources
RUN pip install --no-cache-dir setuptools==69.5.1

# Verify pkg_resources works
RUN python -c "import pkg_resources; print('pkg_resources OK')"

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway sets PORT env var
CMD ["python", "collector_loop.py"]
