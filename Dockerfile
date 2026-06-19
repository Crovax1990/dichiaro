FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock* ./
RUN pip install --no-cache-dir uv && uv sync --frozen

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8501
CMD ["uv", "run", "streamlit", "run", "frontend/app.py", "--server.address=0.0.0.0"]
