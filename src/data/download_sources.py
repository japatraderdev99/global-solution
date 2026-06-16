from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path


SEN2FIRE_URL = "https://zenodo.org/records/10881058/files/Sen2Fire.zip?download=1"
SEN2FIRE_MD5 = "135be2af2a8577c6deb12cbd7cc76c1a"
FLOGA_REPO_URL = "https://github.com/Orion-AI-Lab/FLOGA"


def md5sum(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        print(f"Arquivo ja existe: {destination}")
        return
    print(f"Baixando {url}")
    print(f"Destino: {destination}")
    urllib.request.urlretrieve(url, destination)


def extract_zip(path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Extraindo {path} em {output_dir}")
    with zipfile.ZipFile(path) as zf:
        zf.extractall(output_dir)


def download_sen2fire(raw_dir: Path, extract: bool) -> None:
    zip_path = raw_dir / "Sen2Fire.zip"
    download(SEN2FIRE_URL, zip_path)
    current_md5 = md5sum(zip_path)
    if current_md5 != SEN2FIRE_MD5:
        raise SystemExit(
            f"Checksum invalido para {zip_path}: esperado {SEN2FIRE_MD5}, obtido {current_md5}"
        )
    print("Checksum Sen2Fire OK.")
    if extract:
        extract_zip(zip_path, raw_dir / "Sen2Fire")


def print_floga_instructions(raw_dir: Path) -> None:
    target = raw_dir / "floga_hdf"
    patches = raw_dir / "floga_patches"
    print("FLOGA exige download dos arquivos .hdf publicados pelo projeto.")
    print(f"Repositorio: {FLOGA_REPO_URL}")
    print(f"Coloque os .hdf em: {target}")
    print("Depois gere patches 256x256 seguindo o README da fonte ou exporte .npz com imagem e mascara.")
    print(f"Diretorio esperado pelo manifesto: {patches}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Baixa fontes publicas da Fase 1.")
    parser.add_argument("--raw-dir", default="data/raw", type=Path)
    parser.add_argument("--sen2fire", action="store_true", help="Baixar Sen2Fire do Zenodo.")
    parser.add_argument("--no-extract", action="store_true", help="Nao extrair zip apos download.")
    parser.add_argument("--floga-info", action="store_true", help="Mostrar instrucoes para FLOGA.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    args.raw_dir.mkdir(parents=True, exist_ok=True)

    if args.sen2fire:
        download_sen2fire(args.raw_dir, extract=not args.no_extract)
    if args.floga_info:
        print_floga_instructions(args.raw_dir)
    if not args.sen2fire and not args.floga_info:
        print("Nada a fazer. Use --sen2fire e/ou --floga-info.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
