# API de inferencia

Servico HTTP da POC Sentinela Orbital. A API combina inferencia orbital com a
leitura do ESP32/Wokwi e devolve classe, probabilidades, risco e recomendacao.

O modelo de visao computacional e carregado como `smallburncnn-1.0` a partir de
`gs://sentinela-orbital-models/small_burn_cnn.pt`. Para demonstracao por URI, a
API usa patches pre-processados em `samples/*.npy` e devolve `unknown` quando a
URI nao corresponde a uma amostra conhecida.

## Executar

```bash
python3 src/api/mock_server.py
```

Para testar localmente com o artefato ja treinado:

```bash
MODEL_PATH=models/small_burn_cnn.pt python3 src/api/mock_server.py
```

## Testar

```bash
curl -s http://127.0.0.1:8000/health
curl -s http://127.0.0.1:8000/sample-response
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  --data @data/samples/api/analyze-request.json
```

## Contrato

O schema OpenAPI fica em `docs/api/openapi.yaml`.

O endpoint principal e `POST /analyze`.

Entradas obrigatorias:

- `image.source_type`
- `image.uri`
- `sensor.device_id`
- `sensor.smoke_ppm`
- `sensor.temperature_c`

Saidas principais:

- `orbital.class`: `fire`, `burned_scar`, `healthy_forest` ou `unknown`
- `orbital.confidence`: confianca de 0 a 1
- `orbital.model_version`: versao do modelo carregado
- `risk.score`: inteiro de 0 a 100
- `risk.level`: `low`, `moderate`, `high` ou `critical`
- `recommendation.action`: acao sugerida para o dashboard
