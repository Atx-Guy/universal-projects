# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies that might be needed by some Python packages
# (e.g., for Pillow, pdf2image, potentially python-magic)
# Add ffmpeg for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libmagic1 \
    poppler-utils \
    ffmpeg \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
# Use --no-cache-dir to reduce image size
# Note: Some requirements might have OS-specific conditions, handle them if necessary
#       We install Pillow separately as it's a common dependency.
RUN pip install --no-cache-dir -r requirements.txt Pillow

# Copy the rest of the application code into the container at /app
COPY . .

# Make port 5000 available to the world outside this container
# Your app.py runs on 0.0.0.0, which is correct for Docker.
# The default Flask port is 5000, Gunicorn default is 8000.
# We'll use Gunicorn as it's in requirements.txt [cite: 4]
EXPOSE 8000

# Define environment variables (optional, can be set at runtime too)
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
# Add any other environment variables your app needs, like DATABASE_URL for production
# ENV DATABASE_URL=your_production_database_url
# ENV SECRET_KEY=your_production_secret_key # Generate a strong secret key

# Command to run the application using Gunicorn (recommended for production)
# Use 0.0.0.0 to ensure the app is accessible from outside the container
# The number of workers (-w 4) can be adjusted based on your server resources
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]