Run pip install --quiet -r requirements.txt
# Use a lightweight Python base image

# 1. Start with the base image (MUST BE FIRST)
FROM python:3.10-slim-bookworm

# 2. Set the working directory
WORKDIR /usr/src/app

# 3. Install system dependencies (git, ffmpeg, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application
COPY . .

# 6. Start the bot
CMD ["python3", "bot.py"]
