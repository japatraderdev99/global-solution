from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mplconfig-"))
os.environ.setdefault("XDG_CACHE_HOME", tempfile.mkdtemp(prefix="xdg-cache-"))

import h5py
import hdf5plugin  # noqa: F401
import matplotlib
import numpy as np
import torch
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_recall_fscore_support
from torch import nn
from torch.nn import functional as F
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

matplotlib.use("Agg")
import matplotlib.pyplot as plt


CLASSES = ["fire", "burned_scar", "healthy_forest"]
CLASS_TO_INDEX = {label: idx for idx, label in enumerate(CLASSES)}
INPUT_DESCRIPTION = "RGB(B4,B3,B2)+NDVI(B8A,B4)+NBR(B8A,B12), 64x64"

# Sentinel-2 common subset. Sen2Fire has 12 image bands plus aerosol; FLOGA
# sen2_60 has the 11 bands available at 60 m, excluding B8 but keeping B8A.
SEN2FIRE_BANDS = {"blue": 1, "green": 2, "red": 3, "nir": 8, "swir2": 11}
FLOGA_BANDS = {"blue": 1, "green": 2, "red": 3, "nir": 7, "swir2": 10}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(False)


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"Manifesto vazio: {path}")
    return rows


def split_h5_ref(ref: str) -> tuple[Path, str, tuple[int, int, int]]:
    path_text, group, tile_text = ref.split("::")
    row_start, col_start, tile_size = (int(value) for value in tile_text.split(":"))
    return Path(path_text), group, (row_start, col_start, tile_size)


def load_sen2fire(path: Path, image_size: int) -> np.ndarray:
    with np.load(path, allow_pickle=False) as npz:
        image = np.asarray(npz["image"], dtype=np.float32)
    selected = select_channels(image, SEN2FIRE_BANDS)
    return stride_to_size(selected, image_size)


def load_floga(ref: str, image_size: int, h5_cache: dict[Path, h5py.File] | None = None) -> np.ndarray:
    path, group, (row_start, col_start, tile_size) = split_h5_ref(ref)
    row_end = row_start + tile_size
    col_end = col_start + tile_size
    step = max(1, tile_size // image_size)
    row_slice = slice(row_start, row_end, step)
    col_slice = slice(col_start, col_end, step)
    if h5_cache is None:
        with h5py.File(path, "r") as h5:
            image = read_floga_channels(h5[group]["sen2_60_post"], row_slice, col_slice)
    else:
        if path not in h5_cache:
            h5_cache[path] = h5py.File(path, "r")
        image = read_floga_channels(h5_cache[path][group]["sen2_60_post"], row_slice, col_slice)
    band_map = {"blue": 0, "green": 1, "red": 2, "nir": 3, "swir2": 4}
    return select_channels(image, band_map)


def read_floga_channels(ds: h5py.Dataset, row_slice: slice, col_slice: slice) -> np.ndarray:
    return np.stack(
        [
            np.asarray(ds[FLOGA_BANDS["blue"], row_slice, col_slice], dtype=np.float32),
            np.asarray(ds[FLOGA_BANDS["green"], row_slice, col_slice], dtype=np.float32),
            np.asarray(ds[FLOGA_BANDS["red"], row_slice, col_slice], dtype=np.float32),
            np.asarray(ds[FLOGA_BANDS["nir"], row_slice, col_slice], dtype=np.float32),
            np.asarray(ds[FLOGA_BANDS["swir2"], row_slice, col_slice], dtype=np.float32),
        ],
        axis=0,
    )


def select_channels(image: np.ndarray, band_map: dict[str, int]) -> np.ndarray:
    blue = image[band_map["blue"]]
    green = image[band_map["green"]]
    red = image[band_map["red"]]
    nir = image[band_map["nir"]]
    swir2 = image[band_map["swir2"]]

    rgb = np.stack([red, green, blue], axis=0) / 10_000.0
    rgb = np.clip(rgb, 0.0, 1.0)
    ndvi = safe_index(nir, red)
    nbr = safe_index(nir, swir2)
    return np.concatenate([rgb, ndvi[None, ...], nbr[None, ...]], axis=0).astype(np.float32)


def stride_to_size(image: np.ndarray, image_size: int) -> np.ndarray:
    height, width = image.shape[-2:]
    if height == image_size and width == image_size:
        return image
    if height >= image_size and width >= image_size and height % image_size == 0 and width % image_size == 0:
        return image[:, :: height // image_size, :: width // image_size][:, :image_size, :image_size]
    return image


def safe_index(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    denom = a + b
    out = np.zeros_like(a, dtype=np.float32)
    np.divide(a - b, denom, out=out, where=np.abs(denom) > 1e-6)
    return np.clip(out, -1.0, 1.0)


def augment(x: torch.Tensor, label: int) -> torch.Tensor:
    if random.random() < 0.5:
        x = torch.flip(x, dims=[2])
    if random.random() < 0.5:
        x = torch.flip(x, dims=[1])
    rotations = random.randint(0, 3)
    if rotations:
        x = torch.rot90(x, rotations, dims=[1, 2])

    if label != CLASS_TO_INDEX["healthy_forest"]:
        gain = 1.0 + random.uniform(-0.08, 0.08)
        x = x.clone()
        x[:3] = torch.clamp(x[:3] * gain, 0.0, 1.0)
        noise = torch.randn_like(x[:3]) * 0.015
        x[:3] = torch.clamp(x[:3] + noise, 0.0, 1.0)
    return x


class SatelliteDataset(Dataset):
    def __init__(self, rows: list[dict[str, str]], image_size: int, train: bool = False, preload: bool = True) -> None:
        self.rows = rows
        self.image_size = image_size
        self.train = train
        self.h5_cache: dict[Path, h5py.File] = {}
        self.cached: list[tuple[torch.Tensor, torch.Tensor]] | None = None
        if preload:
            self.cached = []
            split_name = "train" if train else "eval"
            for idx, row in enumerate(self.rows, start=1):
                self.cached.append(self.load_row(row))
                if idx % 250 == 0 or idx == len(self.rows):
                    print(f"preload_{split_name}={idx}/{len(self.rows)}", flush=True)

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor]:
        row = self.rows[index]
        if self.cached is not None:
            x, y = self.cached[index]
            if self.train:
                x = augment(x, int(y.item()))
            return x, y
        return self.load_row(row, apply_augmentation=self.train)

    def load_row(self, row: dict[str, str], apply_augmentation: bool = False) -> tuple[torch.Tensor, torch.Tensor]:
        if row["source"] == "sen2fire":
            x_np = load_sen2fire(Path(row["image_path"]), self.image_size)
        elif row["source"] == "floga":
            x_np = load_floga(row["image_path"], self.image_size, self.h5_cache)
        else:
            raise ValueError(f"Fonte nao suportada: {row['source']}")

        x = torch.from_numpy(x_np)
        if x.shape[-2:] != (self.image_size, self.image_size):
            x = F.interpolate(x.unsqueeze(0), size=(self.image_size, self.image_size), mode="bilinear", align_corners=False).squeeze(0)
        y = CLASS_TO_INDEX[row["label"]]
        if apply_augmentation:
            x = augment(x, y)
        return x, torch.tensor(y, dtype=torch.long)

    def __del__(self) -> None:
        for handle in getattr(self, "h5_cache", {}).values():
            try:
                handle.close()
            except Exception:
                pass


class SmallBurnCNN(nn.Module):
    def __init__(self, in_channels: int = 5, num_classes: int = 3) -> None:
        super().__init__()
        self.features = nn.Sequential(
            conv_block(in_channels, 16),
            nn.MaxPool2d(2),
            conv_block(16, 32),
            nn.MaxPool2d(2),
            conv_block(32, 64),
            nn.MaxPool2d(2),
            conv_block(64, 96),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(0.2), nn.Linear(96, num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))


def conv_block(in_channels: int, out_channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    )


def rebalance_train_rows(rows: list[dict[str, str]], healthy_cap: int, seed: int) -> list[dict[str, str]]:
    rng = random.Random(seed)
    by_label: dict[str, list[dict[str, str]]] = {label: [] for label in CLASSES}
    for row in rows:
        by_label[row["label"]].append(row)

    healthy = list(by_label["healthy_forest"])
    rng.shuffle(healthy)
    selected = by_label["fire"] + by_label["burned_scar"] + healthy[:healthy_cap]
    rng.shuffle(selected)
    return selected


def make_sampler(rows: list[dict[str, str]]) -> WeightedRandomSampler:
    counts = Counter(row["label"] for row in rows)
    weights = [1.0 / counts[row["label"]] for row in rows]
    return WeightedRandomSampler(weights=weights, num_samples=len(rows), replacement=True)


def train_one_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    model.train()
    total_loss = 0.0
    total_seen = 0
    for x, y in loader:
        x = x.to(device)
        y = y.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()
        total_loss += float(loss.item()) * y.size(0)
        total_seen += y.size(0)
    return total_loss / max(total_seen, 1)


@torch.no_grad()
def predict(model: nn.Module, loader: DataLoader, device: torch.device) -> tuple[list[int], list[int]]:
    model.eval()
    y_true: list[int] = []
    y_pred: list[int] = []
    for x, y in loader:
        logits = model(x.to(device))
        pred = torch.argmax(logits, dim=1).cpu().tolist()
        y_pred.extend(pred)
        y_true.extend(y.tolist())
    return y_true, y_pred


def compute_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=list(range(len(CLASSES))),
        zero_division=0,
    )
    per_class = {}
    for idx, label in enumerate(CLASSES):
        per_class[label] = {
            "precision": round(float(precision[idx]), 6),
            "recall": round(float(recall[idx]), 6),
            "f1": round(float(f1[idx]), 6),
            "support": int(support[idx]),
        }

    matrix = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES)))).astype(int).tolist()
    return {
        "overall": {
            "accuracy": round(float(accuracy_score(y_true, y_pred)), 6),
            "f1_macro": round(float(f1_score(y_true, y_pred, labels=list(range(len(CLASSES))), average="macro", zero_division=0)), 6),
            "f1_weighted": round(float(f1_score(y_true, y_pred, labels=list(range(len(CLASSES))), average="weighted", zero_division=0)), 6),
        },
        "per_class": per_class,
        "confusion_matrix": {"labels": CLASSES, "matrix": matrix},
    }


def write_confusion_matrix_png(matrix: list[list[int]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(5.8, 4.8))
    data = np.asarray(matrix)
    im = ax.imshow(data, cmap="YlOrRd")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    ax.set_xticks(range(len(CLASSES)), CLASSES, rotation=25, ha="right")
    ax.set_yticks(range(len(CLASSES)), CLASSES)
    ax.set_xlabel("Predito")
    ax.set_ylabel("Real")
    ax.set_title("Matriz de confusao - teste")
    threshold = data.max() / 2 if data.size and data.max() else 0
    for row in range(data.shape[0]):
        for col in range(data.shape[1]):
            color = "white" if data[row, col] > threshold else "black"
            ax.text(col, row, str(data[row, col]), ha="center", va="center", color=color)
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def save_model(model: nn.Module, path: Path, args: argparse.Namespace, metrics: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_name": "SmallBurnCNN",
            "model_state_dict": model.state_dict(),
            "classes": CLASSES,
            "input": INPUT_DESCRIPTION,
            "image_size": args.image_size,
            "metrics": metrics["overall"],
            "band_maps": {"sen2fire": SEN2FIRE_BANDS, "floga": FLOGA_BANDS},
        },
        path,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Treina CNN pequena para fire/burned_scar/healthy_forest.")
    parser.add_argument("--manifest", type=Path, default=Path("data/processed/classification_manifest.csv"))
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--image-size", type=int, default=64)
    parser.add_argument("--healthy-train-cap", type=int, default=650)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=568506)
    parser.add_argument("--model-out", type=Path, default=Path("models/small_burn_cnn.pt"))
    parser.add_argument("--metrics-out", type=Path, default=Path("docs/eda/model_metrics.json"))
    parser.add_argument("--confusion-out", type=Path, default=Path("docs/eda/confusion_matrix.png"))
    parser.add_argument("--no-preload", action="store_true", help="Desativa cache em memoria dos tensores 5x64.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    seed_everything(args.seed)
    device = torch.device("cpu")

    rows = read_manifest(args.manifest)
    train_full = [row for row in rows if row["split"] == "train"]
    train_rows = rebalance_train_rows(train_full, args.healthy_train_cap, args.seed)
    val_rows = [row for row in rows if row["split"] == "val"]
    test_rows = [row for row in rows if row["split"] == "test"]

    preload = not args.no_preload
    train_ds = SatelliteDataset(train_rows, image_size=args.image_size, train=True, preload=preload)
    val_ds = SatelliteDataset(val_rows, image_size=args.image_size, train=False, preload=preload)
    test_ds = SatelliteDataset(test_rows, image_size=args.image_size, train=False, preload=preload)

    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=make_sampler(train_rows), num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)

    model = SmallBurnCNN().to(device)
    full_counts = Counter(row["label"] for row in train_rows)
    class_weights = torch.tensor(
        [math.sqrt(len(train_rows) / max(full_counts[label], 1)) for label in CLASSES],
        dtype=torch.float32,
        device=device,
    )
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)

    best_state = None
    best_val_f1 = -1.0
    for epoch in range(1, args.epochs + 1):
        loss = train_one_epoch(model, train_loader, optimizer, criterion, device)
        y_val, pred_val = predict(model, val_loader, device)
        val_f1 = f1_score(y_val, pred_val, labels=list(range(len(CLASSES))), average="macro", zero_division=0)
        print(f"epoch={epoch:02d} loss={loss:.4f} val_f1_macro={val_f1:.4f}", flush=True)
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)

    y_test, pred_test = predict(model, test_loader, device)
    metrics = compute_metrics(y_test, pred_test)

    rebalancing = (
        f"Treino com undersample de healthy_forest para {args.healthy_train_cap} amostras; "
        "minorias preservadas; WeightedRandomSampler inverso a frequencia; pesos de classe sqrt; "
        "augmentacao com flips/rotacao e jitter leve em fire/burned_scar."
    )
    payload = {
        "meta": {
            "generated_at": utc_now(),
            "framework": "pytorch",
            "model": "SmallBurnCNN",
            "epochs": args.epochs,
            "input": INPUT_DESCRIPTION,
            "rebalancing": rebalancing,
            "notes": (
                "Treino CPU-friendly em dados 60m ja existentes; classes fire e burned_scar vêm de fontes diferentes, "
                "e burned_scar possui suporte muito baixo no teste."
            ),
        },
        "classes": CLASSES,
        "split_evaluated": "test",
        "dataset": {"train": len(train_rows), "val": len(val_rows), "test": len(test_rows)},
        **metrics,
    }

    args.metrics_out.parent.mkdir(parents=True, exist_ok=True)
    args.metrics_out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    write_confusion_matrix_png(metrics["confusion_matrix"]["matrix"], args.confusion_out)
    save_model(model, args.model_out, args, payload)

    print(f"model: {args.model_out}")
    print(f"metrics: {args.metrics_out}")
    print(f"confusion_matrix: {args.confusion_out}")
    print(json.dumps(payload["overall"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
