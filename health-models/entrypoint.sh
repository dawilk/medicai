#!/bin/sh

DEFAULT_MODEL="llama3.2"
MODEL=${1:-$DEFAULT_MODEL}
MODEL_DIR="/root/health-models"
MODEL_FILE="$MODEL_DIR/Modelfile"

# Start the Ollama service in the background
echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for the Ollama service to be ready
echo "Waiting for Ollama service to be ready..."
until ollama ps >/dev/null 2>&1; do
    sleep 2
done

# Run the commands only if the health model doesn't already exist
if ! ollama show health >/dev/null 2>&1; then
    echo "Creating the health model..."
    # echo a warning that this may take a few minutes
    echo "WARNING: The default language model is ~2GB and can take a while to download depending on your internet connection."
    # replace the FROM line in the Modelfile with the model name
    sed -i "s|FROM .*|FROM $MODEL|" $MODEL_FILE
    ollama create health -f $MODEL_FILE
fi

# Keep the Ollama service running in the foreground
echo "Starting the health model..."
ollama run health

# Wait for the Ollama service to keep running in the foreground
echo "Ollama service is running. Keeping the container alive..."
wait $OLLAMA_PID
