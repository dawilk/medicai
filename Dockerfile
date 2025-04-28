FROM python:3.13-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .

# Expose the port Gradio will run on
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
