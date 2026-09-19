FROM python:3.11-slim

WORKDIR /app

# Install system utilities including rclone
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    rclone \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

EXPOSE 8080

VOLUME ["/app/data", "/mnt/nas_doc", "/mnt/nas_media", "/mnt/nas_movie"]

ENTRYPOINT ["gdrive-hub"]
CMD ["portal", "--host", "0.0.0.0", "--port", "8080"]
