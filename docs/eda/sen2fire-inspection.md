# EDA gerada — manifesto de classificacao

> Autor: Guilherme Yamada Dantas — RM568506

Total de amostras: **2447**.

## Proveniencia

- Gerado em: `2026-06-16T23:27:19Z`
- Manifesto: `data/processed/classification_manifest_sen2fire_only.csv`
- Limiar fire: `0.01`
- Limiar burned_scar: `0.02`
- Limiar healthy_forest: `0.001`

## Contagem por classe

| Item | Total |
|---|---:|
| fire | 325 |
| healthy_forest | 2122 |

## Contagem por split

| Item | Total |
|---|---:|
| test | 501 |
| train | 1448 |
| val | 498 |

## Contagem por fonte

| Item | Total |
|---|---:|
| sen2fire | 2447 |

## Matriz split x classe

| Split | fire | healthy_forest |
|---|---:|---:|
| test | 96 | 405 |
| train | 143 | 1305 |
| val | 86 | 412 |

## Auditoria de grupos

Nenhum `group_id` aparece em mais de um split.

## Exemplos por classe

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
