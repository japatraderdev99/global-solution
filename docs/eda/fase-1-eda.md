# EDA — Fase 1 Dados

> Autor: Guilherme Yamada Dantas — RM568506

## Objetivo

Validar a viabilidade de um dataset de classificacao em tres classes para o
contrato da API:

- `fire`
- `burned_scar`
- `healthy_forest`

## Resultado da analise inicial

A decisao e usar **classificacao derivada de mascaras**. As fontes mais defensaveis
para a POC sao Sen2Fire e FLOGA porque ambas trabalham com imagens orbitais e
rotulos espaciais, com licencas publicas.

## Fontes

| Fonte | Uso | Evidencia de adequacao |
|---|---|---|
| Sen2Fire | `fire` e negativos | 2.466 patches Sentinel, 512 x 512, 13 bandas, com splits por area |
| FLOGA | `burned_scar` e negativos | 326 eventos, Sentinel-2/MODIS antes/depois, mascara de area queimada |

## EDA de fonte

### Sen2Fire

| Split | Patches |
|---|---:|
| treino | 1.458 |
| validacao | 504 |
| teste | 504 |
| **total** | **2.466** |

Observacao: a fonte separa os splits por areas de estudo diferentes, reduzindo
risco de vazamento geografico entre treino e avaliacao.

### FLOGA

| Item | Valor |
|---|---:|
| eventos de incendio | 326 |
| periodo | 2017-2021 |
| label 0 | pixel nao queimado |
| label 1 | pixel queimado |
| label 2 | pixel ambiguidade/outro evento do mesmo ano |

Observacao: pixels com valor `2` devem ser ignorados ou excluidos do calculo de
rotulo do patch.

## Como gerar a EDA real apos download

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

## Status

- Decisao de dataset: fechada.
- Scripts de preparo e EDA: criados.
- Download integral do Sen2Fire: concluido e validado por checksum.
- Download integral do FLOGA: concluido em HDF5 e validado por leitura local.
- EDA real por classe: gerada em `docs/eda/eda_summary.json`.
- Artefatos-resumo versionaveis: `docs/eda/eda_summary.json`,
  `docs/eda/fase-1-eda-gerada.md` e `docs/eda/class_distribution.png`.
- Verificacoes Sen2Fire fechadas: arquivo ZIP com MD5
  `135be2af2a8577c6deb12cbd7cc76c1a`, 2.466 arquivos `.npz`, chaves internas
  `image`, `aerosol` e `label`, mascara `label == 1`, split bruto reproduzido
  como 1.458/504/504.
- Artefatos de validacao Sen2Fire-only: `docs/eda/sen2fire-validacao-real.md`,
  `docs/eda/sen2fire_inspection.json`, `docs/eda/sen2fire-inspection.md` e
  `docs/eda/sen2fire_class_distribution.png`.
- Verificacoes FLOGA fechadas: 5 arquivos `.h5`, 326 eventos, mascara `label`
  com valores `0`, `1` e `2`, tiles 512 x 512, `label == 1` como area queimada
  e `label == 2` ignorado.
- Manifesto completo: 5.900 amostras, com `fire=325`, `burned_scar=69`,
  `healthy_forest=5506` e `group_leakage=0`.

## Criterio para liberar Fase 2

A Fase 2 so deve iniciar quando o manifesto gerado tiver:

- pelo menos uma amostra em cada uma das tres classes;
- splits `train`, `val` e `test`;
- F1 macro como metrica principal planejada, alem de accuracy e matriz de confusao.
