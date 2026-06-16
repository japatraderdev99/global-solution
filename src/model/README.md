# Treino da CNN de classificacao

Autor: Guilherme Yamada Dantas — RM568506

## Entrada escolhida

O treino usa uma entrada comum entre Sen2Fire (`.npz`) e FLOGA (`.h5`) com 5 canais em `64x64`:

- RGB aproximado: `B4`, `B3`, `B2`
- `NDVI = (B8A - B4) / (B8A + B4)`
- `NBR = (B8A - B12) / (B8A + B12)`

`B8A` foi usado como NIR porque aparece nas duas fontes; a banda `B8` do Sentinel-2 não aparece no FLOGA 60m.

## Comando

```bash
python3 src/model/train.py \
  --manifest data/processed/classification_manifest.csv \
  --epochs 8 \
  --batch-size 64 \
  --healthy-train-cap 650 \
  --model-out models/small_burn_cnn.pt \
  --metrics-out docs/eda/model_metrics.json \
  --confusion-out docs/eda/confusion_matrix.png
```

## Rebalanceamento

O split de treino preserva todas as amostras `fire` e `burned_scar`, reduz `healthy_forest` para 650 amostras, usa `WeightedRandomSampler` inverso a frequencia, pesos de classe na loss e augmentacao leve com reforco nas classes minoritarias.

As metricas finais sao calculadas no split `test` completo, sem undersampling.
