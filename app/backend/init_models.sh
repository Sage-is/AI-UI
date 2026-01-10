#!/usr/bin/env bash

# Runtime Model Initialization Script
# Moved from Dockerfile RUN commands to enable faster Docker builds

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd "$SCRIPT_DIR" || exit

echo "🤖 Initializing AI models and dependencies at runtime..."

# Function to check if model download is needed
check_model_cache() {
    local cache_dir="$1"
    local model_name="$2"
    
    if [ -d "$cache_dir" ] && [ "$(ls -A "$cache_dir" 2>/dev/null)" ]; then
        echo "✅ $model_name already cached in $cache_dir"
        return 0  # Model exists
    else
        echo "📥 $model_name not found, downloading to $cache_dir"
        return 1  # Model needs download
    fi
}

# Function to check if PyTorch is installed
check_pytorch() {
    if python -c "import torch; print('PyTorch version:', torch.__version__)" 2>/dev/null; then
        echo "✅ PyTorch already installed"
        return 0
    else
        echo "📥 PyTorch not found, installing..."
        return 1
    fi
}

# 0. Install PyTorch if needed
echo "🔥 Checking PyTorch installation..."
if ! check_pytorch; then
    echo "Installing PyTorch..."
    TORCH_URL="https://download.pytorch.org/whl/cpu"
    if [ "$USE_CUDA" = "true" ]; then
        TORCH_URL="https://download.pytorch.org/whl/$USE_CUDA_DOCKER_VER"
        echo "CUDA enabled, using $TORCH_URL"
    fi
    pip3 install torch torchvision torchaudio --index-url $TORCH_URL --no-cache-dir --break-system-packages
    echo "✅ PyTorch installed"
fi

# 1. Initialize SentenceTransformers model
echo "🔍 Checking SentenceTransformers model..."
if ! check_model_cache "$SENTENCE_TRANSFORMERS_HOME" "SentenceTransformers ($RAG_EMBEDDING_MODEL)"; then
    echo "Downloading SentenceTransformers model: $RAG_EMBEDDING_MODEL"
    python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')"
    echo "✅ SentenceTransformers model downloaded"
fi

# 2. Initialize Whisper model
echo "🎤 Checking Whisper model..."
whisper_cache="$WHISPER_MODEL_DIR"
if ! check_model_cache "$whisper_cache" "Whisper ($WHISPER_MODEL)"; then
    echo "Downloading Whisper model: $WHISPER_MODEL"
    python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])"
    echo "✅ Whisper model downloaded"
fi

# 3. Initialize Tiktoken encoding
echo "🔤 Checking Tiktoken encoding..."
tiktoken_cache="$TIKTOKEN_CACHE_DIR"
if ! check_model_cache "$tiktoken_cache" "Tiktoken ($TIKTOKEN_ENCODING_NAME)"; then
    echo "Downloading Tiktoken encoding: $TIKTOKEN_ENCODING_NAME"
    python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])"
    echo "✅ Tiktoken encoding downloaded"
fi

echo "🚀 All models initialized successfully!"
