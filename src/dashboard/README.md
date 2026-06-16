# Dashboard — Sentinela Orbital

Interface de monitoramento ambiental em tempo real. Consome a API de análise de risco via `POST /analyze` e exibe classificação orbital, leituras de sensor e mapa de risco.

## Como executar

**1. Suba o mock (ou API real) em outra aba de terminal:**

```bash
python3 src/api/mock_server.py
```

**2. Sirva o dashboard pela raiz do repositorio:**

```bash
python3 -m http.server 8080 --directory .
```

**3. Acesse no navegador:**

```
http://localhost:8080/src/dashboard/index.html
```

> Abrir `index.html` diretamente via `file://` pode ser bloqueado pelo navegador
> ao fazer requisições para `http://localhost:8000`. Use sempre o servidor HTTP.
> A vista de Dados tambem precisa acessar `docs/eda/eda_summary.json`, por isso
> o servidor deve partir da raiz do projeto.

## Estrutura

| Arquivo      | Responsabilidade                        |
|--------------|-----------------------------------------|
| `index.html` | Estrutura e componentes do painel       |
| `style.css`  | Tema dark, layout sidebar + mapa        |
| `app.js`     | Comunicação com API, Leaflet, DOM       |

## Funcionalidades

- **Carga automática**: ao abrir, busca `GET /sample-response` e popula todos os painéis.
- **Mapa interativo**: marcador colorido por nível de risco com animação de pulso para alertas críticos/altos.
- **Nova análise**: formulário envia `POST /analyze` com URI de imagem e leituras de sensor; atualiza todos os painéis e reposiciona o mapa.
- **Status da API**: indicador no topo mostra se a API está acessível.

## Variáveis de ambiente / configuração

O endereço base da API está em `app.js`, linha 3:

```js
const API_BASE = 'http://localhost:8000';
```

Altere para o endpoint real do Cloud Run após o deploy da Fase 3.
