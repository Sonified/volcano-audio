FROM python:3.11.11

WORKDIR /app

# Upgrade pip and ensure setuptools is current
RUN pip install --upgrade pip setuptools

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Verify setuptools/pkg_resources is available
RUN python -c "import pkg_resources; print('pkg_resources OK')"

# Copy application code
COPY . .

# Railway sets PORT env var
CMD ["python", "collector_loop.py"]
