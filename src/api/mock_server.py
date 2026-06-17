from __future__ import annotations

import json
import math
import os
import shutil
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

# 0.0.0.0 + porta via $PORT para rodar no Cloud Run; localmente cai em 8000.
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8000"))
SERVICE = "sentinela-orbital-api"
VERSION = "0.1.0"
MAX_BODY_BYTES = 1_000_000
MODEL_VERSION = os.environ.get("MODEL_VERSION", "smallburncnn-1.0")
MODEL_GCS_URI = os.environ.get("MODEL_GCS_URI", "gs://sentinela-orbital-models/small_burn_cnn.pt")
MODEL_PATH = Path(os.environ.get("MODEL_PATH", "/tmp/small_burn_cnn.pt"))
LOCAL_MODEL_CANDIDATES = (Path("small_burn_cnn.pt"), Path("models/small_burn_cnn.pt"), Path("../models/small_burn_cnn.pt"))
BASE_DIR = Path(__file__).resolve().parent
CLASSES = ["fire", "burned_scar", "healthy_forest"]
SAMPLE_PATCHES = {
    "amazon-fire-001.jpg": BASE_DIR / "samples" / "fire.npy",
    "samples/amazon-fire-001.jpg": BASE_DIR / "samples" / "fire.npy",
    "amazon-burned-scar-001.jpg": BASE_DIR / "samples" / "burned_scar.npy",
    "samples/amazon-burned-scar-001.jpg": BASE_DIR / "samples" / "burned_scar.npy",
    "amazon-scar-001.jpg": BASE_DIR / "samples" / "burned_scar.npy",
    "samples/amazon-scar-001.jpg": BASE_DIR / "samples" / "burned_scar.npy",
    "amazon-healthy-001.jpg": BASE_DIR / "samples" / "healthy_forest.npy",
    "samples/amazon-healthy-001.jpg": BASE_DIR / "samples" / "healthy_forest.npy",
    "amazon-forest-001.jpg": BASE_DIR / "samples" / "healthy_forest.npy",
    "samples/amazon-forest-001.jpg": BASE_DIR / "samples" / "healthy_forest.npy",
}
_MODEL: nn.Module | None = None
_MODEL_LOAD_ERROR: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class SmallBurnCNN(nn.Module):
    def __init__(self, in_channels: int = 5, num_classes: int = 3) -> None:
        super().__init__()
        self.features = nn.Sequential(
            conv_block(in_channels, 16),
            nn.MaxPool2d(2),
            conv_block(16, 32),
            nn.MaxPool2d(2),
            conv_block(32, 64),
            nn.MaxPool2d(2),
            conv_block(64, 96),
            nn.AdaptiveAvgPool2d(1),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Dropout(0.2), nn.Linear(96, num_classes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.head(self.features(x))


def conv_block(in_channels: int, out_channels: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
        nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1, bias=False),
        nn.BatchNorm2d(out_channels),
        nn.ReLU(inplace=True),
    )


def parse_gcs_uri(uri: str) -> tuple[str, str] | None:
    if not uri.startswith("gs://"):
        return None
    path = uri[5:]
    if "/" not in path:
        return None
    bucket, blob = path.split("/", 1)
    return bucket, blob


def ensure_model_file() -> Path:
    if MODEL_PATH.exists():
        return MODEL_PATH

    for candidate in LOCAL_MODEL_CANDIDATES:
        if candidate.exists():
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(candidate, MODEL_PATH)
            return MODEL_PATH

    parsed = parse_gcs_uri(MODEL_GCS_URI)
    if parsed:
        bucket, blob = parsed
        try:
            from google.cloud import storage

            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            storage.Client().bucket(bucket).blob(blob).download_to_filename(str(MODEL_PATH))
            return MODEL_PATH
        except Exception as exc:
            print(f"[aviso] download autenticado do modelo falhou: {exc}")

        public_url = f"https://storage.googleapis.com/{bucket}/{blob}"
        try:
            MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(public_url, MODEL_PATH)
            return MODEL_PATH
        except Exception as exc:
            print(f"[aviso] download publico do modelo falhou: {exc}")

    raise FileNotFoundError(f"Modelo indisponivel em {MODEL_PATH} ou {MODEL_GCS_URI}")


def get_model() -> nn.Module | None:
    global _MODEL, _MODEL_LOAD_ERROR
    if _MODEL is not None:
        return _MODEL
    if _MODEL_LOAD_ERROR is not None:
        return None

    try:
        model_path = ensure_model_file()
        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
        model = SmallBurnCNN()
        model.load_state_dict(checkpoint["model_state_dict"])
        model.eval()
        _MODEL = model
        print(f"Modelo carregado: {model_path} ({MODEL_VERSION})")
        return _MODEL
    except Exception as exc:
        _MODEL_LOAD_ERROR = str(exc)
        print(f"[erro] modelo indisponivel: {_MODEL_LOAD_ERROR}")
        return None


def normalize_uri(image_uri: str) -> str:
    normalized = image_uri.strip().lower()
    if normalized.startswith("gs://"):
        normalized = normalized.rsplit("/", 1)[-1]
    elif "://" in normalized:
        normalized = normalized.split("://", 1)[1].split("/", 1)[-1]
    return normalized


def patch_for_uri(image_uri: str) -> Path | None:
    normalized = normalize_uri(image_uri)
    if normalized in SAMPLE_PATCHES:
        return SAMPLE_PATCHES[normalized]
    basename = normalized.rsplit("/", 1)[-1]
    return SAMPLE_PATCHES.get(basename)


def unknown_orbital_result() -> dict[str, Any]:
    return {
        "class": "unknown",
        "confidence": 0.0,
        "probabilities": {"fire": 0.0, "burned_scar": 0.0, "healthy_forest": 0.0},
        "model_version": MODEL_VERSION,
    }


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


def orbital_result(image_uri: str) -> dict[str, Any]:
    patch_path = patch_for_uri(image_uri)
    if patch_path is None or not patch_path.exists():
        return unknown_orbital_result()

    model = get_model()
    if model is None:
        return unknown_orbital_result()

    patch = np.load(patch_path).astype(np.float32)
    if patch.shape == (64, 64, 5):
        patch = np.transpose(patch, (2, 0, 1))
    if patch.shape != (5, 64, 64):
        raise ValueError(f"Patch invalido para inferencia: {patch_path} shape={patch.shape}")

    x = torch.from_numpy(patch).unsqueeze(0)
    with torch.no_grad():
        probs_tensor = torch.softmax(model(x), dim=1).squeeze(0)
    probs = [float(value) for value in probs_tensor.tolist()]
    best_idx = int(np.argmax(probs))
    probabilities = {label: round(probs[idx], 6) for idx, label in enumerate(CLASSES)}
    return {
        "class": CLASSES[best_idx],
        "confidence": round(probs[best_idx], 6),
        "probabilities": probabilities,
        "model_version": MODEL_VERSION,
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
    orbital = orbital_result(image_uri)
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
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": SERVICE,
                    "version": VERSION,
                    "model_version": MODEL_VERSION,
                    "model_loaded": get_model() is not None,
                },
            )
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
    get_model()
    server = HTTPServer((HOST, PORT), Handler)
    print(f"API de inferencia em http://{HOST}:{PORT}")
    print("Rotas: GET /health, GET /sample-response, POST /analyze")
    server.serve_forever()


if __name__ == "__main__":
    run()
