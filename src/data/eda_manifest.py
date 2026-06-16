from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def read_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def median(values: list[float]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    mid = n // 2
    if n % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def summarize(rows: list[dict[str, str]], meta: dict) -> dict:
    by_label = Counter(row["label"] for row in rows)
    by_split = Counter(row["split"] for row in rows)
    by_source = Counter(row["source"] for row in rows)
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    examples: dict[str, list[str]] = defaultdict(list)
    group_splits: dict[str, set[str]] = defaultdict(set)

    ratios: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        matrix[row["split"]][row["label"]] += 1
        if row.get("group_id"):
            group_splits[row["group_id"]].add(row["split"])
        if len(examples[row["label"]]) < 5:
            examples[row["label"]].append(row["image_path"])
        try:
            ratios[row["label"]].append(float(row["positive_ratio"]))
        except (TypeError, ValueError):
            pass

    ratio_summary = {}
    for label, values in ratios.items():
        ordered = sorted(values)
        ratio_summary[label] = {
            "min": ordered[0],
            "median": median(ordered),
            "max": ordered[-1],
        }

    return {
        "meta": meta,
        "total_samples": len(rows),
        "class_counts": dict(sorted(by_label.items())),
        "split_counts": dict(sorted(by_split.items())),
        "source_counts": dict(sorted(by_source.items())),
        "split_class_matrix": {split: dict(sorted(labels.items())) for split, labels in sorted(matrix.items())},
        "positive_ratio_by_label": ratio_summary,
        "examples_by_label": dict(sorted(examples.items())),
        "group_leakage": {
            group: sorted(splits)
            for group, splits in sorted(group_splits.items())
            if len(splits) > 1
        },
    }


def write_json(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")


def md_table(mapping: dict[str, int]) -> str:
    lines = ["| Item | Total |", "|---|---:|"]
    for key, value in mapping.items():
        lines.append(f"| {key} | {value} |")
    return "\n".join(lines)


def write_markdown(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# EDA gerada — manifesto de classificacao",
        "",
        "> Autor: Guilherme Yamada Dantas — RM568506",
        "",
        f"Total de amostras: **{summary['total_samples']}**.",
        "",
        "## Proveniencia",
        "",
        f"- Gerado em: `{summary['meta']['generated_at']}`",
        f"- Manifesto: `{summary['meta']['manifest_path']}`",
        f"- Limiar fire: `{summary['meta']['thresholds']['fire']}`",
        f"- Limiar burned_scar: `{summary['meta']['thresholds']['burned_scar']}`",
        f"- Limiar healthy_forest: `{summary['meta']['thresholds']['negative']}`",
        "",
        "## Contagem por classe",
        "",
        md_table(summary["class_counts"]),
        "",
        "## Contagem por split",
        "",
        md_table(summary["split_counts"]),
        "",
        "## Contagem por fonte",
        "",
        md_table(summary["source_counts"]),
        "",
        "## Matriz split x classe",
        "",
    ]

    labels = sorted(summary["class_counts"])
    lines.append("| Split | " + " | ".join(labels) + " |")
    lines.append("|---" + "|---:" * len(labels) + "|")
    for split, counts in summary["split_class_matrix"].items():
        lines.append("| " + split + " | " + " | ".join(str(counts.get(label, 0)) for label in labels) + " |")

    lines.extend(["", "## Auditoria de grupos", ""])
    if summary["group_leakage"]:
        lines.append("Grupos encontrados em mais de um split:")
        lines.extend(f"- `{group}`: {', '.join(splits)}" for group, splits in summary["group_leakage"].items())
    else:
        lines.append("Nenhum `group_id` aparece em mais de um split.")

    lines.extend(["", "## Exemplos por classe", ""])
    for label, examples in summary["examples_by_label"].items():
        lines.append(f"### {label}")
        lines.extend(f"- `{example}`" for example in examples)
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_chart(summary: dict, path: Path) -> None:
    try:
        os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp(prefix="mplconfig-"))
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("[aviso] matplotlib indisponivel; grafico nao foi gerado.")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    labels = list(summary["class_counts"].keys())
    values = [summary["class_counts"][label] for label in labels]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(labels, values, color=["#ff4d3d", "#f3c14b", "#4fd08a"][: len(labels)])
    ax.set_title("Distribuicao por classe")
    ax.set_ylabel("Amostras")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gera EDA a partir do manifesto de classificacao.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, default=Path("docs/eda/eda_summary.json"))
    parser.add_argument("--out-md", type=Path, default=Path("docs/eda/fase-1-eda-gerada.md"))
    parser.add_argument("--out-chart", type=Path, default=Path("docs/eda/class_distribution.png"))
    parser.add_argument("--fire-threshold", type=float, default=0.01)
    parser.add_argument("--burned-threshold", type=float, default=0.02)
    parser.add_argument("--negative-threshold", type=float, default=0.001)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    rows = read_manifest(args.manifest)
    if not rows:
        raise SystemExit("Manifesto vazio.")
    summary = summarize(
        rows,
        meta={
            "generated_at": utc_now(),
            "manifest_path": str(args.manifest),
            "thresholds": {
                "fire": args.fire_threshold,
                "burned_scar": args.burned_threshold,
                "negative": args.negative_threshold,
            },
            "sources": {
                "sen2fire": {
                    "doi": "10.5281/zenodo.10881058",
                    "license": "CC-BY-4.0",
                },
                "floga": {
                    "repository": "https://github.com/Orion-AI-Lab/FLOGA",
                    "data_license": "CC-BY-4.0",
                    "code_license": "MIT",
                },
            },
        },
    )
    write_json(summary, args.out_json)
    write_markdown(summary, args.out_md)
    if args.out_chart:
        write_chart(summary, args.out_chart)
    print(f"EDA JSON: {args.out_json}")
    print(f"EDA Markdown: {args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
