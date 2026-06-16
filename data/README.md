# data/

Pasta de dados do **Sentinela Orbital**.

> Datasets grandes **não** são versionados no git (ver `.gitignore`). Aqui ficam apenas
> amostras pequenas, metadados e instruções de download.

## Estrutura prevista

```
data/
├── samples/      # poucas imagens de exemplo (versionadas) para demo/teste
├── raw/          # dataset bruto baixado (ignorado pelo git)
└── processed/    # dataset pré-processado pelo pipeline (ignorado pelo git)
```

## Dataset

A Fase 1 usa classificacao derivada de mascaras orbitais:

- **Sen2Fire**: fonte principal para `fire` e negativos.
- **FLOGA**: fonte complementar para `burned_scar` e negativos.

A decisao completa esta em `docs/decisoes/01-dataset-framework-fase-1.md`.
Os scripts ficam em `src/data/`.
