from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any


# 0.0.0.0 + porta via $PORT para rodar no Cloud Run; localmente cai em 8000.
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
SERVICE = "sentinela-orbital-api"
VERSION = "0.1.0"
MAX_BODY_BYTES = 1_000_000


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def classify_sensor(smoke_ppm: float, temperature_c: float) -> tuple[str, list[str]]:
    factors: list[str] = []

    if smoke_ppm >= 800:
        factors.append("critical_smoke")
    elif smoke_ppm >= 400:
        factors.append("high_smoke")
    elif smoke_ppm >= 150:
        factors.append("moderate_smoke")

    if temperature_c >= 50:
        factors.append("critical_temperature")
    elif temperature_c >= 38:
        factors.append("high_temperature")
    elif temperature_c >= 32:
        factors.append("moderate_temperature")

    if "critical_smoke" in factors or "critical_temperature" in factors:
        return "critical", factors
    if "high_smoke" in factors or "high_temperature" in factors:
        return "high", factors
    if factors:
        return "moderate", factors
    return "low", factors


def mock_orbital_result(image_uri: str) -> dict[str, Any]:
    normalized = image_uri.lower()
    if "scar" in normalized or "queimada" in normalized or "burned" in normalized:
        return {
            "class": "burned_scar",
            "confidence": 0.84,
            "probabilities": {"fire": 0.08, "burned_scar": 0.84, "healthy_forest": 0.08},
            "model_version": "mock-0.1.0",
        }
    if "healthy" in normalized or "forest" in normalized or "saudavel" in normalized:
        return {
            "class": "healthy_forest",
            "confidence": 0.88,
            "probabilities": {"fire": 0.05, "burned_scar": 0.07, "healthy_forest": 0.88},
            "model_version": "mock-0.1.0",
        }
    return {
        "class": "fire",
        "confidence": 0.91,
        "probabilities": {"fire": 0.91, "burned_scar": 0.06, "healthy_forest": 0.03},
        "model_version": "mock-0.1.0",
    }


def risk_from_inputs(orbital_class: str, sensor_level: str, factors: list[str]) -> dict[str, Any]:
    score = 10

    if orbital_class == "fire":
        score += 50
        factors.append("orbital_fire_detected")
    elif orbital_class == "burned_scar":
        score += 30
        factors.append("orbital_burned_scar_detected")
    elif orbital_class == "healthy_forest":
        factors.append("orbital_healthy_forest")

    score += {"low": 0, "moderate": 15, "high": 30, "critical": 40}[sensor_level]
    score = max(0, min(100, score))

    if score >= 85:
        level = "critical"
        label = "Risco critico"
        action = "dispatch_review"
        message = "Priorizar verificacao da area e confirmar foco ativo."
    elif score >= 65:
        level = "high"
        label = "Risco alto"
        action = "review"
        message = "Revisar a area com prioridade e acompanhar proximas leituras."
    elif score >= 35:
        level = "moderate"
        label = "Risco moderado"
        action = "monitor"
        message = "Manter monitoramento e comparar com novas amostras."
    else:
        level = "low"
        label = "Risco baixo"
        action = "monitor"
        message = "Sem alerta imediato; manter acompanhamento de rotina."

    return {
        "risk": {"score": score, "level": level, "label": label, "factors": factors},
        "recommendation": {"action": action, "message": message},
    }


def validate_payload(payload: dict[str, Any]) -> str | None:
    if not isinstance(payload.get("image"), dict):
        return "Campo obrigatorio ausente: image"
    if not payload["image"].get("uri"):
        return "Campo obrigatorio ausente: image.uri"
    if not isinstance(payload.get("sensor"), dict):
        return "Campo obrigatorio ausente: sensor"

    sensor = payload["sensor"]
    for field in ("device_id", "smoke_ppm", "temperature_c"):
        if field not in sensor:
            return f"Campo obrigatorio ausente: sensor.{field}"
    try:
        smoke_ppm = float(sensor["smoke_ppm"])
        temperature_c = float(sensor["temperature_c"])
    except (TypeError, ValueError):
        return "sensor.smoke_ppm e sensor.temperature_c devem ser numericos"

    if not math.isfinite(smoke_ppm) or smoke_ppm < 0:
        return "sensor.smoke_ppm deve ser um numero maior ou igual a 0"
    if not math.isfinite(temperature_c) or temperature_c < -20 or temperature_c > 80:
        return "sensor.temperature_c deve estar entre -20 e 80"

    for field, lower, upper in (("latitude", -90, 90), ("longitude", -180, 180)):
        if sensor.get(field) is None:
            continue
        try:
            value = float(sensor[field])
        except (TypeError, ValueError):
            return f"sensor.{field} deve ser numerico"
        if not math.isfinite(value) or value < lower or value > upper:
            return f"sensor.{field} deve estar entre {lower} e {upper}"
    return None


def analyze(payload: dict[str, Any]) -> dict[str, Any]:
    sensor = payload["sensor"]
    image_uri = str(payload["image"]["uri"])
    smoke_ppm = float(sensor["smoke_ppm"])
    temperature_c = float(sensor["temperature_c"])
    sensor_level, sensor_factors = classify_sensor(smoke_ppm, temperature_c)
    orbital = mock_orbital_result(image_uri)
    risk = risk_from_inputs(orbital["class"], sensor_level, sensor_factors)

    location = None
    if sensor.get("latitude") is not None and sensor.get("longitude") is not None:
        location = {"latitude": sensor["latitude"], "longitude": sensor["longitude"]}

    return {
        "request_id": payload.get("request_id"),
        "status": "ok",
        "generated_at": utc_now(),
        "orbital": orbital,
        "sensor": {
            "device_id": sensor["device_id"],
            "smoke_ppm": smoke_ppm,
            "temperature_c": temperature_c,
            "humidity_pct": sensor.get("humidity_pct"),
            "signal_level": sensor_level,
        },
        "risk": risk["risk"],
        "recommendation": risk["recommendation"],
        "location": location,
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": SERVICE, "version": VERSION})
            return
        if self.path == "/sample-response":
            sample = analyze(
                {
                    "request_id": "demo-001",
                    "image": {"source_type": "sample", "uri": "amazon-fire-001.jpg"},
                    "sensor": {
                        "device_id": "esp32-wokwi-001",
                        "smoke_ppm": 620,
                        "temperature_c": 42.6,
                        "humidity_pct": 31.4,
                        "latitude": -3.4653,
                        "longitude": -62.2159,
                    },
                }
            )
            self._send_json(200, sample)
            return
        self._send_json(404, {"status": "error", "error": {"code": "not_found", "message": "Rota inexistente."}})

    def do_POST(self) -> None:
        if self.path != "/analyze":
            self._send_json(404, {"status": "error", "error": {"code": "not_found", "message": "Rota inexistente."}})
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > MAX_BODY_BYTES:
            self._send_json(
                413,
                {
                    "status": "error",
                    "error": {
                        "code": "payload_too_large",
                        "message": "Envie image.uri apontando para Cloud Storage ou URL publica.",
                    },
                },
            )
            return

        try:
            raw_body = self.rfile.read(content_length)
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json(400, {"status": "error", "error": {"code": "invalid_json", "message": "JSON invalido."}})
            return

        validation_error = validate_payload(payload)
        if validation_error:
            self._send_json(
                400,
                {"status": "error", "error": {"code": "invalid_payload", "message": validation_error}},
            )
            return

        self._send_json(200, analyze(payload))

    def log_message(self, format: str, *args: Any) -> None:
        print("%s - %s" % (self.address_string(), format % args))


def run() -> None:
    server = HTTPServer((HOST, PORT), Handler)
    print(f"Mock API em http://{HOST}:{PORT}")
    print("Rotas: GET /health, GET /sample-response, POST /analyze")
    server.serve_forever()


if __name__ == "__main__":
    run()
