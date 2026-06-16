from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np


CLASSES = ("fire", "burned_scar", "healthy_forest")
LABEL_KEYS = ("label", "labels", "mask", "masks", "gt", "ground_truth", "y")


@dataclass
class ManifestRow:
    sample_id: str
    source: str
    group_id: str
    split: str
    label: str
    positive_ratio: float
    image_path: str
    mask_path: str


def stable_split(text: str) -> str:
    value = int(hashlib.sha1(text.encode("utf-8")).hexdigest()[:8], 16) % 100
    if value < 70:
        return "train"
    if value < 85:
        return "val"
    return "test"


def sen2fire_split(path: Path) -> str:
    parts = {part.lower() for part in path.parts}
    if "scene3" in parts or "scene_3" in parts:
        return "val"
    if "scene4" in parts or "scene_4" in parts:
        return "test"
    if "scene1" in parts or "scene2" in parts or "scene_1" in parts or "scene_2" in parts:
        return "train"
    name = path.name.lower()
    if "scene_3" in name:
        return "val"
    if "scene_4" in name:
        return "test"
    return "train"


def sen2fire_group_id(path: Path) -> str:
    parts = [part.lower() for part in path.parts]
    for part in parts:
        if part in {"scene1", "scene2", "scene3", "scene4"}:
            return part
    match = re.search(r"scene[_-]?([1-4])", path.stem.lower())
    if match:
        return f"scene{match.group(1)}"
    return "sen2fire_unknown_scene"


def floga_event_id(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        rel = path

    if len(rel.parts) > 1:
        return rel.parts[0]

    stem = path.stem.lower()
    cleanup_patterns = (
        r"([_-](patch|tile|crop)[_-]?\d+.*)$",
        r"([_-]row[_-]?\d+[_-]col[_-]?\d+.*)$",
        r"([_-]\d+[_-]\d+)$",
    )
    for pattern in cleanup_patterns:
        cleaned = re.sub(pattern, "", stem)
        if cleaned != stem and cleaned:
            return cleaned
    return stem


def find_label_array(npz: np.lib.npyio.NpzFile) -> np.ndarray:
    lower_keys = {key.lower(): key for key in npz.files}
    for expected in LABEL_KEYS:
        if expected in lower_keys:
            return np.asarray(npz[lower_keys[expected]])
    if len(npz.files) == 1:
        return np.asarray(npz[npz.files[0]])
    raise ValueError(f"Nenhuma mascara encontrada. Chaves disponiveis: {', '.join(npz.files)}")


def positive_ratio(mask: np.ndarray, positive_values: set[int], ignore_values: set[int] | None = None) -> float:
    values = np.asarray(mask)
    if values.ndim > 2:
        values = np.squeeze(values)
    ignore_values = ignore_values or set()
    valid = np.ones(values.shape, dtype=bool)
    for ignore in ignore_values:
        valid &= values != ignore
    total = int(valid.sum())
    if total == 0:
        return 0.0
    positive = np.zeros(values.shape, dtype=bool)
    for value in positive_values:
        positive |= values == value
    return float((positive & valid).sum() / total)


def label_from_ratio(ratio: float, positive_label: str, positive_threshold: float, negative_threshold: float) -> str | None:
    if ratio >= positive_threshold:
        return positive_label
    if ratio <= negative_threshold:
        return "healthy_forest"
    return None


def iter_npz(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.npz"))


def sen2fire_rows(root: Path, fire_threshold: float, negative_threshold: float) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for path in iter_npz(root):
        try:
            with np.load(path, allow_pickle=False) as npz:
                mask = find_label_array(npz)
                ratio = positive_ratio(mask, {1})
        except Exception as exc:
            print(f"[aviso] pulando {path}: {exc}")
            continue
        label = label_from_ratio(ratio, "fire", fire_threshold, negative_threshold)
        if label is None:
            continue
        rows.append(
            ManifestRow(
                sample_id=path.stem,
                source="sen2fire",
                group_id=sen2fire_group_id(path),
                split=sen2fire_split(path),
                label=label,
                positive_ratio=ratio,
                image_path=str(path),
                mask_path=str(path),
            )
        )
    return rows


def floga_rows(root: Path, burned_threshold: float, negative_threshold: float) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for path in iter_npz(root):
        try:
            with np.load(path, allow_pickle=False) as npz:
                mask = find_label_array(npz)
                ratio = positive_ratio(mask, {1}, ignore_values={2})
        except Exception as exc:
            print(f"[aviso] pulando {path}: {exc}")
            continue
        label = label_from_ratio(ratio, "burned_scar", burned_threshold, negative_threshold)
        if label is None:
            continue
        event_id = floga_event_id(path, root)
        rows.append(
            ManifestRow(
                sample_id=path.stem,
                source="floga",
                group_id=event_id,
                split=stable_split(event_id),
                label=label,
                positive_ratio=ratio,
                image_path=str(path),
                mask_path=str(path),
            )
        )
    return rows


def floga_h5_rows(
    root: Path,
    burned_threshold: float,
    negative_threshold: float,
    tile_size: int,
    min_valid_ratio: float,
) -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    if not root.exists():
        return rows

    try:
        import hdf5plugin  # noqa: F401
        import h5py
    except ImportError as exc:
        print(f"[aviso] h5py/hdf5plugin indisponivel para FLOGA HDF5: {exc}")
        return rows

    for path in sorted(root.rglob("*.h5")):
        try:
            with h5py.File(path, "r") as h5:
                for year in sorted(h5.keys()):
                    year_group = h5[year]
                    for event in sorted(year_group.keys(), key=lambda value: int(value) if value.isdigit() else value):
                        event_group = year_group[event]
                        if "label" not in event_group:
                            print(f"[aviso] FLOGA sem label: {path}::{year}/{event}")
                            continue
                        mask = event_group["label"][0]
                        height, width = mask.shape
                        event_id = f"floga_{year}_{event}"
                        split = stable_split(event_id)
                        for row_start in range(0, height - tile_size + 1, tile_size):
                            for col_start in range(0, width - tile_size + 1, tile_size):
                                tile = mask[row_start : row_start + tile_size, col_start : col_start + tile_size]
                                ratio = positive_ratio(tile, {1}, ignore_values={2})
                                valid_ratio = float((tile != 2).sum() / tile.size)
                                if valid_ratio < min_valid_ratio:
                                    continue
                                label = label_from_ratio(ratio, "burned_scar", burned_threshold, negative_threshold)
                                if label is None:
                                    continue
                                tile_ref = f"{path}::{year}/{event}::{row_start}:{col_start}:{tile_size}"
                                rows.append(
                                    ManifestRow(
                                        sample_id=f"{event_id}_r{row_start}_c{col_start}",
                                        source="floga",
                                        group_id=event_id,
                                        split=split,
                                        label=label,
                                        positive_ratio=ratio,
                                        image_path=tile_ref,
                                        mask_path=tile_ref,
                                    )
                                )
        except Exception as exc:
            print(f"[aviso] pulando HDF5 FLOGA {path}: {exc}")
            continue
    return rows


def demo_rows() -> list[ManifestRow]:
    rows: list[ManifestRow] = []
    for split in ("train", "val", "test"):
        for label, ratio in (("fire", 0.12), ("burned_scar", 0.18), ("healthy_forest", 0.0)):
            rows.append(
                ManifestRow(
                    sample_id=f"demo_{split}_{label}",
                    source="demo",
                    group_id=f"demo_{split}",
                    split=split,
                    label=label,
                    positive_ratio=ratio,
                    image_path=f"data/samples/demo/{split}_{label}.npz",
                    mask_path=f"data/samples/demo/{split}_{label}.npz",
                )
            )
    return rows


def write_manifest(rows: list[ManifestRow], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(ManifestRow.__dataclass_fields__.keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "sample_id": row.sample_id,
                    "source": row.source,
                    "group_id": row.group_id,
                    "split": row.split,
                    "label": row.label,
                    "positive_ratio": f"{row.positive_ratio:.8f}",
                    "image_path": row.image_path,
                    "mask_path": row.mask_path,
                }
            )


def assert_all_classes(rows: list[ManifestRow]) -> None:
    labels = {row.label for row in rows}
    missing = [label for label in CLASSES if label not in labels]
    if missing:
        raise SystemExit(f"Manifesto sem classes obrigatorias: {', '.join(missing)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera manifesto de classificacao a partir de mascaras.")
    parser.add_argument("--sen2fire-dir", type=Path, default=Path("data/raw/Sen2Fire"))
    parser.add_argument("--floga-dir", type=Path, default=Path("data/raw/floga_patches"))
    parser.add_argument("--out", type=Path, default=Path("data/processed/classification_manifest.csv"))
    parser.add_argument("--fire-threshold", type=float, default=0.01)
    parser.add_argument("--burned-threshold", type=float, default=0.02)
    parser.add_argument("--negative-threshold", type=float, default=0.001)
    parser.add_argument("--floga-tile-size", type=int, default=512)
    parser.add_argument("--floga-min-valid-ratio", type=float, default=0.5)
    parser.add_argument("--require-all-classes", action="store_true")
    parser.add_argument("--demo", action="store_true", help="Gera manifesto pequeno para teste do pipeline.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.demo:
        rows = demo_rows()
    else:
        rows = []
        rows.extend(sen2fire_rows(args.sen2fire_dir, args.fire_threshold, args.negative_threshold))
        rows.extend(floga_rows(args.floga_dir, args.burned_threshold, args.negative_threshold))
        rows.extend(
            floga_h5_rows(
                args.floga_dir,
                args.burned_threshold,
                args.negative_threshold,
                args.floga_tile_size,
                args.floga_min_valid_ratio,
            )
        )

    if not rows:
        raise SystemExit("Nenhuma amostra encontrada. Verifique data/raw/ ou use --demo para teste.")
    if args.require_all_classes:
        assert_all_classes(rows)

    write_manifest(rows, args.out)
    print(f"Manifesto gerado: {args.out}")
    print(f"Amostras: {len(rows)}")
    for label in CLASSES:
        print(f"{label}: {sum(1 for row in rows if row.label == label)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
