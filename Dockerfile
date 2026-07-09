FROM python:3.9-slim

# Install system dependencies & OpenJDK-17 for PySpark JVM context
RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set Java Home configurations
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

WORKDIR /code

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source directories and files
COPY src/ ./src
COPY data/ ./data
COPY app.py .
COPY run.sh .

# Grant execution permissions to the startup script
RUN chmod +x run.sh

# Expose Streamlit dashboard port (Hugging Face Spaces default port)
EXPOSE 7860

# Launch unified services
CMD ["./run.sh"]
