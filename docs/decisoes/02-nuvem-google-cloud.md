# Decisao tecnica 02 — Plataforma de nuvem (Fase 3)

> Autor: Guilherme Yamada Dantas — RM568506

## Decisao

A API serverless da Fase 3 sera publicada no **Google Cloud**, usando
**Cloud Run** para a inferencia e **Cloud Storage** para os artefatos.

| Necessidade | Servico Google Cloud |
|---|---|
| Inferencia HTTP do modelo (container com FastAPI/Flask + ONNX) | **Cloud Run** |
| Armazenamento do modelo treinado e imagens de amostra | **Cloud Storage (GCS)** |
| Endpoint HTTPS publico | URL gerada pelo proprio Cloud Run |

## Justificativa

- **Adequacao ao modelo de ML.** O Cloud Run executa um container, o que permite
  empacotar o modelo (CNN exportada para ONNX) com suas dependencias sem limite
  apertado de tamanho de pacote — mais simples do que funcoes com restricao de
  empacotamento para uma carga de visao computacional.
- **Serverless de verdade.** Escala a zero quando ocioso (sem custo parado) e
  sobe sob demanda; atende o criterio de "computacao em nuvem / serverless / APIs"
  da rubrica.
- **Free tier suficiente.** Cloud Run e Cloud Storage tem camada gratuita que cobre
  com folga o uso de uma POC academica (poucas requisicoes, poucos MB de modelo).
- **Contrato preservado.** A interface entre backend e front-end e o
  `docs/api/openapi.yaml`. A troca de plataforma **nao altera o contrato**: o
  dashboard so aponta `API_BASE` para a URL do Cloud Run apos o deploy.

## Impacto

- **Front-end:** trocar uma constante (`API_BASE`) — nenhuma mudanca estrutural.
- **Contrato:** termos de armazenamento alinhados a nuvem escolhida
  (`image.source_type`: `gcs | url | sample`).
- **Fase 3:** deploy via `gcloud run deploy` (a partir de Dockerfile), bucket no GCS
  para o artefato do modelo, e configuracao de **CORS** na aplicacao para a origem
  do dashboard.

## Fallback

Caso a publicacao na nuvem fique indisponivel no momento da gravacao do video,
o mesmo container roda localmente expondo a mesma API — a demonstracao do fluxo
ponta a ponta fica preservada.
