# Validacao real do Sen2Fire

> Autor: Guilherme Yamada Dantas — RM568506

## Integridade

| Item | Valor |
|---|---:|
| Arquivo | `data/raw/Sen2Fire.zip` |
| Tamanho | 6.346.737.700 bytes |
| MD5 esperado | `135be2af2a8577c6deb12cbd7cc76c1a` |
| MD5 obtido | `135be2af2a8577c6deb12cbd7cc76c1a` |

## Estrutura real do ZIP

| Item | Valor |
|---|---:|
| Membros totais | 2.466 |
| Extensao | `.npz` |
| `scene1` | 864 patches |
| `scene2` | 594 patches |
| `scene3` | 504 patches |
| `scene4` | 504 patches |

O split bruto oficial foi reproduzido pelo mapeamento:

| Split | Cenas | Patches |
|---|---|---:|
| train | `scene1`, `scene2` | 1.458 |
| val | `scene3` | 504 |
| test | `scene4` | 504 |

## Chaves e mascara

Cada patch inspecionado contem:

| Chave | Shape | Tipo | Uso |
|---|---|---|---|
| `image` | `(12, 512, 512)` | `int16` | bandas orbitais |
| `aerosol` | `(512, 512)` | `float32` | camada auxiliar |
| `label` | `(512, 512)` | `uint8` | mascara de fogo |

A mascara `label` usa `0` para fundo/sem fogo e `1` para fogo. Portanto, a regra
do pipeline `label == 1` esta correta para o Sen2Fire real.

## Distribuicao bruta de fogo

| Cena | Patches | Patches com fogo | Pixels positivos | Razao positiva |
|---|---:|---:|---:|---:|
| `scene1` | 864 | 115 | 7.779.854 | 0,03434929 |
| `scene2` | 594 | 38 | 1.784.143 | 0,01145785 |
| `scene3` | 504 | 94 | 4.694.012 | 0,03552824 |
| `scene4` | 504 | 102 | 7.632.679 | 0,05777055 |

## Manifesto Sen2Fire-only

Com os limiares da Fase 1 (`fire >= 0.01`, `healthy_forest <= 0.001`), patches
intermediarios sao descartados para reduzir ruido no primeiro treino.

| Classe | Amostras |
|---|---:|
| `fire` | 325 |
| `healthy_forest` | 2.122 |
| `burned_scar` | 0 |
| **total** | **2.447** |

O manifesto Sen2Fire-only foi gerado em
`data/processed/classification_manifest_sen2fire_only.csv` e sua EDA de inspeção
esta em `docs/eda/sen2fire_inspection.json`.

## Conclusao

Os achados pendentes sobre o Sen2Fire foram fechados: o formato real e o encoding
da mascara batem com o pipeline, e o split oficial 1.458/504/504 foi reproduzido.
A classe `burned_scar` continua bloqueada ate a ingestao real do FLOGA.
