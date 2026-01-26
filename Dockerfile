# Multi-stage build for smaller final image
FROM python:3.10-slim as builder

# Install Poetry
RUN pip install --no-cache-dir poetry==1.7.0

# Set working directory
WORKDIR /app

# Copy poetry files
COPY pyproject.toml ./

# Install dependencies (no dev dependencies in production)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-dev

# Final stage
FROM python:3.10-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY bot.py ./
COPY scripts/ ./scripts/
COPY data/adp_board.csv ./data/
COPY data/hooper_two_players_only.sql ./data/

# Create directories for data persistence
RUN mkdir -p data/images data/backups

# Run as non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

CMD ["python", "bot.py"]
