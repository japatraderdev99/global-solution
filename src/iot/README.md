# ESP32 simulado no Wokwi

Autor: Guilherme Yamada Dantas - RM568506

Esta pasta fecha a etapa de IoT da POC com um ESP32 simulado no Wokwi. O dispositivo le:

- DHT22 para temperatura e umidade;
- potenciometro como simulador de fumaca em ppm;
- LED e buzzer como alerta local quando o risco sensor fica alto.

O firmware monta o mesmo JSON consumido por `POST /analyze` na API:

- `image.source_type`
- `image.uri`
- `sensor.device_id`
- `sensor.smoke_ppm`
- `sensor.temperature_c`
- `sensor.humidity_pct`
- `sensor.latitude`
- `sensor.longitude`

## Como abrir no Wokwi

1. Acesse https://wokwi.com/projects/new/esp32.
2. Substitua o conteudo do sketch pelo arquivo `sketch.ino`.
3. Substitua o diagrama pelo arquivo `diagram.json`.
4. Adicione `libraries.txt` com a biblioteca `DHT sensor library for ESPx`.
5. Clique em Run e use o Serial Monitor.

O modo padrao nao depende de rede: ele imprime o payload JSON no Serial Monitor a cada 5 segundos. Isso evita travar a demo caso o simulador nao consiga acessar a API.

## Envio HTTP opcional

Para enviar direto para uma API publica, edite no topo de `sketch.ino`:

```cpp
static const bool SEND_HTTP = true;
static const char *API_URL = "https://sua-api-publica/analyze";
```

No Wokwi web, `localhost` nao aponta para a maquina local. Para demo local, use o payload impresso no Serial ou exponha a API por uma URL publica temporaria.

## Validacao local do contrato

Com a API local rodando:

```bash
python3 src/api/mock_server.py
```

em outro terminal:

```bash
curl -s -X POST http://127.0.0.1:8000/analyze \
  -H "Content-Type: application/json" \
  --data @src/iot/sample-payload.json
```

## Roteiro curto para o video

1. Mostrar o ESP32 no Wokwi com DHT22 e controle de fumaca.
2. Subir o valor do potenciometro.
3. Mostrar o Serial Monitor emitindo `smoke_ppm`, `temperature_c` e o JSON.
4. Mostrar o mesmo contrato chegando na API/dashboard.
