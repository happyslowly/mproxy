# mproxy

Dynamic reverse proxy for llama.cpp with automatic model swapping.

## Usage

```bash
# Install
uv add mproxy

# Configure ~/.config/mproxy/config.toml
[models.gpt-oss-20b]
repo = "microsoft/DialoGPT-medium"

[models.gpt-oss-20b.args]
"--ctx-size" = 4096
"--gpu-layers" = 35

# Run
mproxy [--port PORT] # default port: 12345
```

## API

- `POST /v1/chat/completions` - OpenAI compatible
- `GET /v1/models` - List models
- `GET /models/running` - Running models  
- `DELETE /models/{name}` - Stop model

Models start on-demand, swap automatically to save memory.
