# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /app

# 3. Copy the requirements file into the container at /app
COPY requirements.txt .

# 4. Install any needed packages specified in requirements.txt
# Using --no-cache-dir to reduce image size
# Using --default-timeout to prevent timeouts on slow networks if any package download is slow
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 5. Copy the rest of the application code into the container at /app
# This includes your sudoku_bot directory and main.py (if it's in the root or sudoku_bot folder)
# Assuming your Procfile specifies `python sudoku_bot/main.py`
# and main.py is inside sudoku_bot directory.
# If main.py is in the root, you might adjust the CMD or Procfile.
COPY . .
# If your sudoku_bot folder is the main source, you could also do:
# COPY sudoku_bot ./sudoku_bot
# COPY requirements.txt .
# COPY Procfile . # If you have other files in root needed in the image

# 6. Make port 8080 available to the world outside this container (optional, not strictly needed for a worker)
# For a worker process like a Telegram bot, exposing a port isn't strictly necessary
# unless you have a health check endpoint or something similar.
# EXPOSE 8080 

# 7. Define environment variable for the bot token (BEST PRACTICE: set this in Hugging Face Space secrets)
# We expect BOT_TOKEN to be set in the Hugging Face Space environment
ENV BOT_TOKEN=""

# 8. Run main.py when the container launches
# This command will be overridden by the Procfile if you use one with Hugging Face.
# However, it's good practice to have a default command.
# If you are using a Procfile (`worker: python sudoku_bot/main.py`),
# Hugging Face will use that. This CMD can be a fallback or for local Docker runs.
CMD ["python", "sudoku_bot/main.py"]
