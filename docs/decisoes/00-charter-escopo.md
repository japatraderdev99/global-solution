# Charter & Escopo — Sentinela Orbital

> Documento de fundação (Fase 0). Define o problema, a solução, o escopo e o plano.
> Autor: Guilherme Yamada Dantas — RM568506 · Sub Global Solution 2026.1 (FIAP).

## 1. Problema

Queimadas e desmatamento na Amazônia são detectados, muitas vezes, tarde demais. Quanto mais cedo um foco é identificado, menor a área queimada e o dano ambiental, econômico e social. A economia espacial gera, diariamente, grandes volumes de imagens orbitais que podem alimentar IA para acelerar essa detecção.

## 2. Pergunta da Global Solution

*Como a Inteligência Artificial e as tecnologias digitais podem transformar a nova economia espacial e gerar impacto positivo na Terra?*

## 3. Solução proposta (POC)

**Sentinela Orbital** — sistema ponta a ponta que:
1. **Classifica imagens orbitais** com um modelo de visão computacional (CNN) em três classes: `fogo`, `cicatriz_queimada`, `floresta_saudavel`.
2. **Recebe sinais de solo** de um sensor simulado em ESP32 (fumaça + temperatura) via Wokwi.
3. **Funde os dois sinais** (orbital + solo) em uma API serverless no Google Cloud, gerando um nível de risco.
4. **Apresenta alertas e mapa de risco** em um dashboard com UI/UX caprichada.

## 4. Cobertura da rubrica (onde está a nota)

| Critério da rubrica | Como o projeto atende |
|---|---|
| Machine Learning / Visão Computacional | CNN treinada para classificar imagens orbitais, com métricas (accuracy, F1, matriz de confusão) |
| Análise de dados / pipeline | Pipeline de ingestão e pré-processamento das imagens + EDA documentada |
| Computação em nuvem / serverless / APIs | Inferência exposta via Google Cloud Run; artefatos em Cloud Storage |
| Sensores / IoT / ESP32 | Firmware ESP32 (Wokwi) publicando fumaça/temperatura |
| Dashboard inteligente | Front-end custom com mapa de risco, métricas e alertas |
| Documentação / comunicação visual | PDF estruturado, diagramas, README por pasta, vídeo de 5 min |

## 5. Escopo

**Dentro do escopo (MVP):**
- Modelo CV de classificação treinado e avaliado em dataset público de imagens (fogo/queimada/floresta).
- Pipeline reproduzível de preparação de dados.
- API serverless no Google Cloud recebendo imagem + leitura de sensor e devolvendo classe + risco.
- ESP32 no Wokwi publicando leituras simuladas.
- Dashboard consumindo a API, com mapa e alertas.
- Documentação completa (PDF + READMEs + diagramas) e roteiro do vídeo.

**Fora do escopo (declarado para honestidade técnica):**
- Detecção em tempo real de satélite ao vivo (usamos imagens de datasets públicos).
- Segmentação pixel-a-pixel (o MVP é classificação; segmentação fica como evolução futura).
- Hardware físico (ESP32 é simulado no Wokwi — declarado abertamente).

## 6. Plano por fases (cronologia)

| Fase | Entrega | Gate |
|---|---|---|
| **0 — Fundação** | Estrutura do repo, README, charter, arquitetura | ◀ você está aqui |
| **1 — Dados** | Dataset escolhido, pipeline de ingestão/pré-processamento, EDA | aprovação |
| **2 — Modelo CV** | CNN treinada, métricas reproduzíveis, artefato salvo | aprovação |
| **3 — Cloud/API** | Cloud Run + Cloud Storage (Google Cloud free tier), inferência online | aprovação |
| **4 — IoT/ESP32** | Firmware Wokwi publicando fumaça/temperatura para a API | aprovação |
| **5 — Dashboard** | Front-end custom: mapa de risco, alertas, métricas | aprovação |
| **6 — Documentação** | PDF de entrega, diagramas, roteiro do vídeo de 5 min | aprovação |
| **7 — Revisão & entrega** | Auditoria geral, push final, gravação do vídeo | entrega |

## 7. Método de trabalho

Desenvolvimento iterativo por fases, com **revisão cruzada e dupla verificação** a cada entrega: construção → revisão crítica → ajuste → validação antes de avançar para a fase seguinte. As decisões técnicas relevantes ficam registradas em `docs/decisoes/`.

## 8. Restrições inegociáveis

- **Autoria:** o projeto é de autoria exclusiva de *Guilherme Yamada Dantas — RM568506*.
- **Originalidade:** trabalho individual e original (semelhança = nota não lançada).
- **Operacionalidade:** todo código testado e funcional.
- **Entregáveis:** MVP funcional + vídeo ≤ 5 min (YouTube Não Listado) + PDF único com links.

## 9. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Dataset orbital pesado/indisponível | Usar dataset público consolidado de wildfire (Kaggle/INPE); versionar só amostras |
| Custos/credenciais de nuvem | Ficar no free tier do Google Cloud; documentar arquitetura; ter fallback local (container rodando o mesmo serviço) |
| Demo do ESP32 falhar no vídeo | Wokwi é reproduzível e gravável; testar antes |
| Overfitting do modelo | Split treino/val/teste, data augmentation, métricas honestas |
