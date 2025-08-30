# mproxy

Dynamic reverse proxy for llama.cpp with automatic model swapping.

## Usage

```bash
# Install
uv add mproxy

# Configure ~/.config/mproxy/config.toml
[models.gpt-3.5-turbo]
repo = "microsoft/DialoGPT-medium"

[models.gpt-3.5-turbo.args]
"--ctx-size" = 4096
"--gpu-layers" = 35

# Run
mproxy
```

## API

- `POST /v1/chat/completions` - OpenAI compatible
- `GET /v1/models` - List models
- `GET /models/running` - Running models  
- `DELETE /models/{name}` - Stop model

Models start on-demand, swap automatically to save memory.