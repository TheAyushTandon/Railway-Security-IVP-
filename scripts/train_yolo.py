"""
YOLO Training Pipeline for Metro Safety AI.
Adheres strictly to PRD Section 13:
- Ultralytics YOLO26n first; YOLO11n fallback; YOLOv8n fallback.
- Deterministic seeding (random=42, numpy=42, torch=42).
- Batch 8 starting point with automatic fallback to 4/2 if CUDA OOM occurs.
- Saves checkpoint to outputs/models/yolo_metro_best.pt.
- Records experiment metadata and training duration.
"""

import os
import sys
import time
import json
import random
import argparse
from pathlib import Path
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = BASE_DIR / "outputs"
MODELS_DIR = OUTPUTS_DIR / "models"
RUNS_DIR = OUTPUTS_DIR / "runs" / "metro"
DATA_YAML = BASE_DIR / "data" / "metro" / "data.yaml"


def set_deterministic_seeds(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            torch.backends.cudnn.deterministic = True
    except ImportError:
        pass


def select_model_architecture() -> str:
    """
    Selects YOLO model architecture adhering to PRD priority:
    1. yolo26n.pt (YOLO26 nano)
    2. yolo11n.pt (YOLO11 nano fallback)
    3. yolov8n.pt (YOLOv8 nano baseline)
    """
    from ultralytics import YOLO

    for candidate in ["yolo26n.pt", "yolo11n.pt", "yolov8n.pt"]:
        try:
            print(f"[ModelSelection] Attempting to initialize {candidate}...")
            model = YOLO(candidate)
            print(f"[ModelSelection] Successfully initialized {candidate}.")
            return candidate
        except Exception as e:
            print(f"[ModelSelection] {candidate} not available ({e}). Trying next fallback...")

    return "yolov8n.pt"


def train_yolo(epochs: int = 30, batch_size: int = 8, imgsz: int = 640, seed: int = 42):
    from ultralytics import YOLO
    import torch

    set_deterministic_seeds(seed)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    if not DATA_YAML.exists():
        print(f"[Train] Error: {DATA_YAML} not found. Run scripts/prepare_dataset.py first.")
        sys.exit(1)

    device = 0 if torch.cuda.is_available() else "cpu"
    device_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
    print(f"[Train] Running on device: {device} ({device_name})")

    arch_name = select_model_architecture()
    model = YOLO(arch_name)

    current_batch = batch_size
    trained = False
    train_results = None
    start_time = time.time()

    while not trained and current_batch >= 2:
        try:
            print(f"[Train] Starting fine-tuning: model={arch_name}, epochs={epochs}, batch={current_batch}, imgsz={imgsz}, seed={seed}...")
            train_results = model.train(
                data=str(DATA_YAML),
                epochs=epochs,
                imgsz=imgsz,
                batch=current_batch,
                seed=seed,
                patience=10,
                device=device,
                project=str(RUNS_DIR),
                name="yolo_metro_baseline",
                exist_ok=True,
                verbose=True
            )
            trained = True
        except RuntimeError as e:
            if "out of memory" in str(e).lower() and current_batch > 2:
                print(f"[Train] CUDA OOM with batch={current_batch}. Retrying with batch={current_batch // 2} per PRD guidance...")
                current_batch = current_batch // 2
                torch.cuda.empty_cache()
            else:
                raise e

    elapsed_sec = round(time.time() - start_time, 2)
    print(f"[Train] Training completed in {elapsed_sec}s.")

    # Locate and copy best weights
    best_pt = RUNS_DIR / "yolo_metro_baseline" / "weights" / "best.pt"
    dest_pt = MODELS_DIR / "yolo_metro_best.pt"

    if best_pt.exists():
        import shutil
        shutil.copy(best_pt, dest_pt)
        print(f"[Train] Exported production checkpoint to: {dest_pt}")
    else:
        # Fallback to last.pt or save model directly
        last_pt = RUNS_DIR / "yolo_metro_baseline" / "weights" / "last.pt"
        if last_pt.exists():
            import shutil
            shutil.copy(last_pt, dest_pt)
            print(f"[Train] Exported last checkpoint to: {dest_pt}")

    # Record experiment metadata per PRD Section 13
    meta = {
        "architecture": arch_name,
        "seed": seed,
        "epochs": epochs,
        "batch_size": current_batch,
        "imgsz": imgsz,
        "device": device_name,
        "dataset_yaml": str(DATA_YAML),
        "duration_seconds": elapsed_sec,
        "checkpoint_path": str(dest_pt)
    }

    meta_file = RUNS_DIR / "yolo_metro_baseline" / "experiment_meta.json"
    with open(meta_file, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"[Train] Experiment metadata saved to: {meta_file}")

    return dest_pt, meta


def main():
    parser = argparse.ArgumentParser(description="Train YOLO detector for Metro Safety AI")
    parser.add_argument("--epochs", type=int, default=15, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=8, help="Batch size (default: 8, drops to 4/2 on OOM)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed")
    args = parser.parse_args()

    train_yolo(epochs=args.epochs, batch_size=args.batch, imgsz=args.imgsz, seed=args.seed)


if __name__ == "__main__":
    main()
