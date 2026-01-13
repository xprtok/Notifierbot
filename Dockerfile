# Use an official lightweight Python image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies (needed for tgcrypto/aiohttp optimization)
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your bot code
COPY bot.py .

# Expose the port used by aiohttp (match the PORT variable in your python script)
EXPOSE 8080

# Command to run the bot
CMD ["python", "bot.py"]
