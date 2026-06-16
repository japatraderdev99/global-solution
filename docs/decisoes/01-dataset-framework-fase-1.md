# Decisao tecnica 01 — Dataset e framework da Fase 1

> Autor: Guilherme Yamada Dantas — RM568506

## Decisao

O MVP usa um **dataset de classificacao derivado de mascaras orbitais**.

Em vez de trocar o contrato da API para segmentacao, o pipeline transforma patches
com mascaras em amostras de classificacao por cobertura dominante:

| Classe do contrato | Fonte principal | Regra inicial |
|---|---|---|
| `fire` | Sen2Fire | patch com proporcao de pixels de fogo acima do limiar |
| `burned_scar` | FLOGA | patch pos-incendio com proporcao de pixels queimados acima do limiar |
| `healthy_forest` | Sen2Fire/FLOGA | patch negativo, sem fogo ativo e sem cicatriz relevante |

Essa escolha resolve a ressalva da Fase 1: Sen2Fire e FLOGA sao bases de
sensoriamento com rotulos por pixel, mas o produto final do pipeline e um
manifesto de **classificacao de imagem** com as tres classes consumidas pela CNN
e pela API.

## Fontes escolhidas

### Sen2Fire

- Fonte: Zenodo, DOI `10.5281/zenodo.10881058`.
- Licenca: Creative Commons Attribution 4.0 International.
- Tamanho: `Sen2Fire.zip`, 6.3 GB.
- Conteudo: 2.466 patches Sentinel, cada patch com 512 x 512 pixels e 13 bandas.
- Split documentado pela fonte: treino 1.458, validacao 504, teste 504.
- Uso no MVP: classe `fire` e parte dos negativos `healthy_forest`.

Validacao real executada em 2026-06-16:

- checksum MD5 confirmado: `135be2af2a8577c6deb12cbd7cc76c1a`;
- estrutura confirmada: 2.466 arquivos `.npz`;
- chaves por patch: `image`, `aerosol` e `label`;
- mascara confirmada: `label` com valores `0` e `1`, usando `1` como fogo;
- split bruto reproduzido por cena: `scene1 + scene2 = 1.458` treino,
  `scene3 = 504` validacao, `scene4 = 504` teste.

### FLOGA

- Fonte: repositorio publico `Orion-AI-Lab/FLOGA`.
- Licencas declaradas no repositorio: MIT para codigo e CC-BY-4.0 para dados.
- Conteudo: 326 eventos de incendio na Grecia entre 2017 e 2021, com imagens
  Sentinel-2/MODIS antes e depois do evento e mascara de area queimada.
- Uso no MVP: classe `burned_scar` e negativos adicionais.

Validacao real executada em 2026-06-16:

- arquivos recebidos em HDF5: `FLOGA_dataset_2017_sen2_60_mod_500.h5` ate
  `FLOGA_dataset_2021_sen2_60_mod_500.h5`;
- total confirmado: 326 eventos;
- chaves por evento: `sen2_60_pre`, `sen2_60_post`, `mod_500_pre`,
  `mod_500_post`, mascaras de nuvem, `sea_mask`, `clc_100_mask` e `label`;
- mascara confirmada: `label` com `0` para nao queimado, `1` para queimado e
  `2` para ambiguidade/outro evento;
- leitura HDF5 requer `hdf5plugin` no ambiente local.

## Regras de rotulagem

Os limiares ficam parametrizados no script para permitir ajuste apos a primeira
EDA real:

- `fire`: razao de pixels positivos em Sen2Fire `>= 0.01`.
- `burned_scar`: razao de pixels queimados em tiles FLOGA `>= 0.0025`.
- `healthy_forest`: razao positiva `<= 0.001`.
- patches intermediarios sao descartados no primeiro treino para reduzir ruido.

O limiar de `burned_scar` foi reduzido apos a EDA real porque o FLOGA vem como
cenas grandes em HDF5. O pipeline usa tiles 512 x 512 e split por evento; assim
a classe queimada fica presente em treino, validacao e teste sem vazamento.

O nome `healthy_forest` e mantido por compatibilidade com o contrato. Tecnicamente,
ele representa patch sem evidencia de fogo/cicatriz relevante dentro das fontes.

## Framework de ML

Escolha: **PyTorch**.

Justificativa:

- leitura e transformacoes customizadas sobre `.npz`/patches sao diretas;
- facilita treinar CNN pequena com controle claro de split e metricas;
- exportacao posterior para ONNX permite inferencia mais leve no container do Cloud Run;
- evita acoplar a Fase 2 a um formato pesado de deploy.

TensorFlow fica como alternativa apenas se a Fase 3 exigir um runtime especifico
mais simples para o servico de nuvem.

## Gates da Fase 1

- manifesto CSV com `sample_id`, `source`, `group_id`, `split`, `label`,
  `positive_ratio`, `image_path` e `mask_path`;
- split por grupo/evento para evitar vazamento entre treino e avaliacao;
- contagem por classe e split;
- verificacao de que as tres classes existem;
- amostras por classe registradas no relatorio de EDA;
- `docs/eda/eda_summary.json` versionavel com bloco `meta` de proveniencia;
- decisao registrada nesta pasta antes do treino.

## Riscos e mitigacoes

| Risco | Mitigacao |
|---|---|
| Dataset grande demais para versionar | versionar apenas scripts, manifestos pequenos e relatorios; `data/raw/` e `data/processed/` ficam ignorados |
| `burned_scar` vir de outra geografia | declarar como POC de sensoriamento orbital e manter evolucao futura para Amazonia/INPE |
| Desbalanceamento entre classes | aplicar amostragem maxima por classe/split no script de preparo |
| Mascara ruidosa em patch misto | descartar faixa intermediaria e registrar limiares usados |
