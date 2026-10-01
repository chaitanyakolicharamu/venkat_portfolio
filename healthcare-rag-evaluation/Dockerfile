FROM python:3.12-slim
WORKDIR /app
ENV OPENBLAS_NUM_THREADS=1
COPY requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
COPY pyproject.toml ./
COPY healthcare_rag ./healthcare_rag
RUN pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8002
CMD ["python", "-m", "uvicorn", "healthcare_rag.api:app", "--host", "0.0.0.0", "--port", "8002"]
