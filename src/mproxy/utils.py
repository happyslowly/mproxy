import socket
from pathlib import Path


def resolve_huggingface(repo: str, model_filename: str | None = None) -> Path:
    hf_root = Path.home() / ".cache" / "huggingface" / "hub"
    model_folder_root = f"models--{repo.replace('/', '--')}"
    ref = hf_root / model_folder_root / "refs" / "main"
    try:
        with open(ref, "r") as f:
            hash = f.read().strip()
    except FileNotFoundError:
        raise FileNotFoundError(f"Model `{repo}` not found in HuggingFace cache")
    if hash:
        model_folder = hf_root / model_folder_root / "snapshots" / hash
        models = [f.name for f in model_folder.iterdir() if f.is_file()]
        if not model_filename:
            if len(models) == 1:
                return model_folder / models[0]
            else:
                raise ValueError(f"Multiple model files found under `{repo}")
        elif model_filename in models:
            return model_folder / model_filename

    raise FileNotFoundError(f"Cannot resolve model `{model_filename}` under `{repo}`")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("localhost", 0))
        port = s.getsockname()[1]
    return port
