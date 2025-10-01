# src/utils.py
import hashlib
import time
import os
import json

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def now_ts():
    return int(time.time())

def safe_join(root, rel):
    # Evita paths fora do diretório raiz
    rel = rel.lstrip("/").replace("..", "")
    return os.path.abspath(os.path.join(root, rel))

def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
