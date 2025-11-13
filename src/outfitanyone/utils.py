# C:\Users\devuser\Codeit\Ad_Content_Creation_Service_Team3\src\outfitanyone\utils.py

import shutil
from pathlib import Path

def save_uploaded_file(uploaded_file, save_dir: Path):
    save_path = save_dir / uploaded_file.name
    with open(save_path, "wb") as f:
        f.write(uploaded_file.read())
    return save_path

def clear_tmp_folder(tmp_dir: Path):
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
