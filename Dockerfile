# 1. Use an official, lightweight Python image
FROM python:3.11-slim

# 2. Set environment variables to optimize Python for Docker
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system dependencies in a single layer to minimize image size
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 5. Copy requirements first to leverage Docker layer caching
COPY requirements.txt /app/

# 6. Install Python dependencies 
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 7. Copy the rest of the application code
COPY . /app/

# 8. Create a non-root user for security best practices
RUN useradd -m djangouser && \
    chown -R djangouser:djangouser /app
USER djangouser

# 9. Expose the port Gunicorn will run on
EXPOSE 8000

# 10. Start the application using Gunicorn (production ready)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "trafic_issues.wsgi:application"]
