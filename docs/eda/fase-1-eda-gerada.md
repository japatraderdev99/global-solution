# EDA gerada — manifesto de classificacao

> Autor: Guilherme Yamada Dantas — RM568506

Total de amostras: **5900**.

## Proveniencia

- Gerado em: `2026-06-16T23:46:18Z`
- Manifesto: `data/processed/classification_manifest.csv`
- Limiar fire: `0.01`
- Limiar burned_scar: `0.0025`
- Limiar healthy_forest: `0.001`

## Contagem por classe

| Item | Total |
|---|---:|
| burned_scar | 69 |
| fire | 325 |
| healthy_forest | 5506 |

## Contagem por split

| Item | Total |
|---|---:|
| test | 1099 |
| train | 3692 |
| val | 1109 |

## Contagem por fonte

| Item | Total |
|---|---:|
| floga | 3453 |
| sen2fire | 2447 |

## Matriz split x classe

| Split | burned_scar | fire | healthy_forest |
|---|---:|---:|---:|
| test | 13 | 96 | 990 |
| train | 38 | 143 | 3511 |
| val | 18 | 86 | 1005 |

## Auditoria de grupos

Nenhum `group_id` aparece em mais de um split.

## Exemplos por classe

### burned_scar
- `data/raw/S2 60m - MODIS 500m/FLOGA_dataset_2017_sen2_60_mod_500.h5::2017/3::0:512:512`
- `data/raw/S2 60m - MODIS 500m/FLOGA_dataset_2017_sen2_60_mod_500.h5::2017/17::0:1024:512`
- `data/raw/S2 60m - MODIS 500m/FLOGA_dataset_2017_sen2_60_mod_500.h5::2017/23::1024:0:512`
- `data/raw/S2 60m - MODIS 500m/FLOGA_dataset_2017_sen2_60_mod_500.h5::2017/45::512:0:512`
- `data/raw/S2 60m - MODIS 500m/FLOGA_dataset_2017_sen2_60_mod_500.h5::2017/51::512:0:512`

### fire
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_10.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_11.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_12.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_13.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_14.npz`

### healthy_forest
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_1.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_18.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_19.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_2.npz`
- `data/raw/Sen2Fire/scene1/scene_1_patch_10_20.npz`
