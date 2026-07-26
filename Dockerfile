FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY researchos ./researchos
COPY scripts ./scripts
RUN pip install --no-cache-dir .

ENV RESEARCHOS_DATA_DIR=/data
EXPOSE 8000
CMD ["uvicorn", "researchos.main:app", "--host", "0.0.0.0", "--port", "8000"]
