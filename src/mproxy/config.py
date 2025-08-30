import os
import tomllib
from pathlib import Path


def load_config():
    if "XDG_CONFIG_HOME" in os.environ:
        config_dir = Path(os.environ["XDG_CONFIG_HOME"])
    else:
        config_dir = Path.home() / ".config"
    config_file = config_dir / "mproxy" / "config.toml"
    try:
        with open(config_file, "rb") as f:
            return tomllib.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"Config file not found: {config_file}")


config = load_config()
