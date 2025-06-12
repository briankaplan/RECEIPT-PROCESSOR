import sys
import json
import logging
import os
import uuid
from pathlib import Path

# Ensure current directory is in sys.path for relative imports
sys.path.append(str(Path(__file__).parent.resolve()))

def load_config(config_path: str) -> dict:
    """Load a JSON config file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"❌ Config file not found: {config_path}")
    with open(config_path) as f:
        return json.load(f)

def setup_logging(log_dir="logs", log_file="receipt_processor.log"):
    """Set up logging to both file and console"""
    Path(log_dir).mkdir(exist_ok=True)
    log_path = Path(log_dir) / log_file

    logging.basicConfig(
        filename=log_path,
        filemode='a',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

    logging.info("📝 Logging initialized")

def save_attachment_file(data: bytes, filename: str, save_dir: str) -> str:
    """
    Save a file from email attachment data to the specified directory with a unique name.
    """
    Path(save_dir).mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{filename}"
    full_path = os.path.join(save_dir, safe_name)

    with open(full_path, "wb") as f:
        f.write(data)

    logging.info(f"📎 Saved attachment to {full_path}")
    return full_path