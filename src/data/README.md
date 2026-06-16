# Dados — pipeline da Fase 1

Scripts para baixar fontes publicas, derivar um manifesto de classificacao e
gerar EDA a partir do manifesto.

## Ordem de execucao

```bash
python3 src/data/download_sources.py --sen2fire
python3 src/data/prepare_classification_manifest.py \
  --sen2fire-dir data/raw/Sen2Fire \
  --floga-dir "data/raw/S2 60m - MODIS 500m" \
  --out data/processed/classification_manifest.csv \
  --burned-threshold 0.0025 \
  --require-all-classes
python3 src/data/eda_manifest.py \
  --manifest data/processed/classification_manifest.csv \
  --burned-threshold 0.0025 \
  --out-json docs/eda/eda_summary.json \
  --out-md docs/eda/fase-1-eda-gerada.md \
  --out-chart docs/eda/class_distribution.png
```

O FLOGA baixado em HDF5 exige `hdf5plugin` para leitura dos arrays comprimidos:

```bash
python3 -m pip install hdf5plugin
```

## Teste sem dataset pesado

```bash
python3 src/data/prepare_classification_manifest.py --demo \
  --out data/processed/classification_manifest_demo.csv
python3 src/data/eda_manifest.py \
  --manifest data/processed/classification_manifest_demo.csv \
  --out-json docs/eda/eda_summary.json \
  --out-md docs/eda/fase-1-eda-gerada.md \
  --out-chart docs/eda/class_distribution.png
```
