# API mock

Mock local da Fase 0.5 para estabilizar o contrato entre backend, ESP32 e
dashboard antes da publicacao no Google Cloud.

## Executar

```bash
python3 src/api/mock_server.py
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
- `risk.score`: inteiro de 0 a 100
- `risk.level`: `low`, `moderate`, `high` ou `critical`
- `recommendation.action`: acao sugerida para o dashboard
