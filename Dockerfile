# Use an official Python runtime as a parent image
FROM python:3.11-slim-bullseye

# Set the working directory in the container
WORKDIR /ShortsTurbo

# 设置/ShortsTurbo目录权限为777
RUN chmod 777 /ShortsTurbo

ENV PYTHONPATH="/ShortsTurbo"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    imagemagick \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Fix security policy for ImageMagick
RUN sed -i '/<policy domain="path" rights="none" pattern="@\*"/d' /etc/ImageMagick-6/policy.xml

# Copy only the requirements.txt first to leverage Docker cache
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the rest of the codebase into the image
COPY . .

# Expose the port the app runs on
EXPOSE 8501

# Command to run the application
CMD ["streamlit", "run", "./webui/Main.py","--browser.serverAddress=127.0.0.1","--server.enableCORS=True","--browser.gatherUsageStats=False"]

# 1. Build the Docker image using the following command
# docker build -t ShortsTurbo .

# 2. Run the Docker container using the following command
## For Linux or MacOS:
# docker run -v $(pwd)/config.toml:/ShortsTurbo/config.toml -v $(pwd)/storage:/ShortsTurbo/storage -p 8501:8501 ShortsTurbo
## For Windows:
# docker run -v ${PWD}/config.toml:/ShortsTurbo/config.toml -v ${PWD}/storage:/ShortsTurbo/storage -p 8501:8501 ShortsTurbo