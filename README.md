# FIAP - Faculdade de Informática e Administração Paulista

<p align="center">
<a href="https://www.fiap.com.br/">
  <img src="assets/logo-fiap.png"
       alt="FIAP - Faculdade de Informática e Administração Paulista"
       width="40%">
</a>
</p>

<br>

# Sentinela Orbital — Detecção Inteligente de Queimadas e Desmatamento

## Sub Global Solution 2026.1 — Inteligência Artificial e a Nova Economia Espacial

## Autor
- **Guilherme Yamada Dantas** — RM568506

## Links
- **Vídeo demonstrativo (YouTube · Não Listado):** https://youtu.be/cfvNSuIKALU

---

## Descrição

**Sentinela Orbital** é uma prova de conceito (POC) que responde à pergunta da Global Solution 2026.1 —
*"Como a Inteligência Artificial e as tecnologias digitais podem transformar a nova economia espacial e gerar impacto positivo na Terra?"* — aplicada a um dos problemas ambientais mais críticos do Brasil: a **detecção precoce de queimadas e desmatamento na Amazônia**.

A solução une **visão computacional sobre imagens orbitais** (classificação de fogo / cicatriz de queimada / floresta saudável) a um **sensor de solo simulado em ESP32** (fumaça e temperatura), consolidando os sinais em uma **API serverless no Google Cloud** e apresentando alertas e mapas de risco em um **dashboard inteligente**.

O resultado é um sistema ponta a ponta que demonstra, de forma integrada, como dados da economia espacial — combinados a IoT, machine learning e computação em nuvem — geram impacto positivo direto na Terra: alerta mais rápido significa resposta mais rápida e menos área queimada.

> POC acadêmica individual desenvolvida para a Sub GS 2026.1 da Graduação ON em Inteligência Artificial da FIAP.

## Arquitetura da Solução

```
        ┌─────────────────────┐
        │  Imagem de satélite  │  (Sentinel-2 / Landsat / INPE)
        └──────────┬──────────┘
                   ▼
        ┌─────────────────────┐
        │  Modelo de Visão     │  CNN → {fogo, cicatriz, floresta}
        │  Computacional (CV)  │
        └──────────┬──────────┘
                   │
   ┌───────────────┤
   ▼               ▼
┌────────────┐  ┌──────────────────────┐
│  ESP32     │  │  API Serverless      │  Cloud Run + Cloud Storage
│  (Wokwi)   │─►│  (Google Cloud)      │  (Google Cloud)
│ fumaça/temp│  │  fusão dos sinais    │
└────────────┘  └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │  Dashboard de Alerta  │  mapa de risco + métricas
                └──────────────────────┘
```

## Estrutura de pastas

- **docs**: documentação textual — charter e escopo, decisões técnicas (ADRs), diagramas, roteiro do vídeo e material do PDF de entrega.
- **src**: todo o código-fonte — pipeline de dados, treino e inferência do modelo de visão computacional, firmware do ESP32 (Wokwi), API serverless (Google Cloud) e dashboard.
- **data**: dados utilizados — amostras de imagens, metadados e bases auxiliares (datasets grandes ficam fora do versionamento, com instruções de download em `data/README.md`).
- **README.md**: este arquivo — guia geral do projeto.

## Links e Observações

- **Repositório oficial**: https://github.com/japatraderdev99/global-solution
- **Vídeo demonstrativo (até 5 min, YouTube Não Listado)**: https://youtu.be/cfvNSuIKALU
- **Decisões técnicas**: documentadas em `docs/decisoes/`.
- **Competição/pódio**: a Sub GS não possui pódio.

## Como executar o código

*Instruções detalhadas serão adicionadas conforme cada módulo for concluído (pré-requisitos, versões, passo a passo de execução do modelo, da API, do ESP32 e do dashboard).*

## Histórico de lançamentos

* 0.1.0 - 16/06/2026
    * Fundação do projeto: estrutura do repositório conforme template FIAP, definição de escopo e arquitetura da solução **Sentinela Orbital**.

---

## Licença

<img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/cc.svg?ref=chooser-v1"><img style="height:22px!important;margin-left:3px;vertical-align:text-bottom;" src="https://mirrors.creativecommons.org/presskit/icons/by.svg?ref=chooser-v1"><p xmlns:cc="http://creativecommons.org/ns#" xmlns:dct="http://purl.org/dc/terms/"><a property="dct:title" rel="cc:attributionURL" href="https://github.com/SabrinaOtoni/TEMPLATE-FIAP-GRAD-ON-IA">MODELO GIT FIAP</a> por <a rel="cc:attributionURL dct:creator" property="cc:attributionName" href="https://fiap.com.br">FIAP</a> está licenciado sobre <a href="http://creativecommons.org/licenses/by/4.0/?ref=chooser-v1" target="_blank" rel="license noopener noreferrer" style="display:inline-block;">Attribution 4.0 International</a>.</p>
