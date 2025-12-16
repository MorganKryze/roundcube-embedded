FROM python:3.11-slim as base

# Create a non-root user
RUN useradd -m appuser
WORKDIR /app

# Install only pip and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Copy source code
COPY src/ ./src/

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 9000

# Run the app
CMD ["python", "-m", "src"]
