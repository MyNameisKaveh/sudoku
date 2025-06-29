# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the requirements file into the container at /app
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 5. Copy the rest of the application code into the container at /app
COPY . .

# 6. Make port available
ENV PORT ${PORT:-7860}
EXPOSE $PORT

# 7. Define environment variables (set these in HF Space secrets or your deployment environment)
ENV BOT_TOKEN=""
ENV FLASK_SECRET_KEY="a_very_secure_default_secret_key_that_you_SHOULD_override"
# It's best practice for FLASK_SECRET_KEY to be set in the environment, not defaulted here.
# The default above is just a placeholder to avoid crashes if not set.

# 8. Run Gunicorn to serve the Flask app
# The module is web_app.app and the Flask instance is named 'app'
CMD ["gunicorn", "--workers", "2", "--bind", "0.0.0.0:$PORT", "web_app.app:app"]
