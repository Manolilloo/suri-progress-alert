#!/usr/bin/env python3
"""Watch the PortWatch VI score for SURI and notify via ntfy."""

from __future__ import annotations

import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

DATA_URL = "https://portwatch-vi.xyz/data/tracker.json"
PAGE_URL = "https://portwatch-vi.xyz/#effort-suri"
STATE_FILE = Path("state.json")

LADDER_TICKS = {"loads": 10.0, "boots": 20.0, "menu": 30.0, "world": 40.0, "playable": 50.0}
LADDER_ORDER = ("loads", "boots", "menu", "world", "playable")
GROUNDWORK_WEIGHTS = {"loader": 0.20, "shaders": 0.28, "graphics": 0.32, "proven": 0.20}
TRACK_WEIGHTS = {"story": 0.35, "render": 0.25, "perf": 0.20, "stability": 0.20}
STABILITY_VALUES = {
    "unknown": 0.0, "constant": 0.0, "often": 0.25,
    "sometimes": 0.55, "rarely": 0.80, "stable": 1.0,
}


def clamp01(value: object) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(number):
        return 0.0
    return min(1.0, max(0.0, number))


def ladder_value(value: object) -> float:
    if value is True:
        return 1.0
    if value is False or value is None:
        return 0.0
    return clamp01(value)


def round_one_decimal(value: float) -> float:
    # Matches JavaScript Math.round(value * 10) / 10, not Python's bankers' rounding.
    rounded = Decimal(str(value * 10)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(rounded / Decimal("10"))


def score_effort(effort: dict) -> float:
    """Mirror PortWatch assets/js/scoring.js scoreEffort()."""
    groundwork = effort.get("groundwork") or {}
    groundwork_fraction = sum(
        weight * clamp01(groundwork.get(key))
        for key, weight in GROUNDWORK_WEIGHTS.items()
    )

    gta = effort.get("gta") or {}
    score = 10.0 * groundwork_fraction
    reached = "groundwork"
    previous_tick = score

    for key in LADDER_ORDER:
        value = ladder_value(gta.get(key))
        if value >= 1.0:
            score = LADDER_TICKS[key]
            previous_tick = score
            reached = key
            continue
        if value > 0.0:
            score = max(score, previous_tick + value * (LADDER_TICKS[key] - previous_tick))
        break

    tracks = {
        "story": clamp01(gta.get("story")),
        "render": clamp01(gta.get("render")),
        "perf": clamp01((float(gta.get("fps") or 0.0)) / 30.0),
        "stability": STABILITY_VALUES.get(str(gta.get("stability") or "unknown"), 0.0),
    }
    quality = sum(TRACK_WEIGHTS[key] * value for key, value in tracks.items())
    if reached == "playable":
        score = 50.0 + quality * 50.0

    manual_score = effort.get("manualScore")
    if isinstance(manual_score, (int, float)) and math.isfinite(float(manual_score)):
        score = min(100.0, max(0.0, float(manual_score)))

    return round_one_decimal(score)


def fetch_tracker() -> dict:
    request = urllib.request.Request(
        DATA_URL,
        headers={"User-Agent": "SURI-Progress-Monitor/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"PortWatch respondió con HTTP {response.status}.")
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("efforts"), list):
        raise RuntimeError("El JSON de PortWatch no tiene el formato esperado.")
    return data


def find_suri(data: dict) -> dict:
    matches = [
        effort for effort in data["efforts"]
        if isinstance(effort, dict) and effort.get("id") == "suri"
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Se esperaba un único proyecto con id 'suri'; encontrados: {len(matches)}."
        )
    return matches[0]


def send_notification(topic: str, previous: float, current: float, updated: str) -> None:
    topic = topic.strip()
    if not topic:
        raise RuntimeError("Falta el secreto NTFY_TOPIC en GitHub Actions.")

    delta = round_one_decimal(current - previous)
    title = f"SURI sube a {current:.1f}%"
    message = (
        f"El progreso de SURI ha aumentado de {previous:.1f}% a {current:.1f}% "
        f"(+{delta:.1f} puntos).\n\n"
        f"Datos de PortWatch actualizados: {updated or 'fecha no indicada'}.\n"
        f"Abrir proyecto: {PAGE_URL}"
    )
    url = "https://ntfy.sh/" + urllib.parse.quote(topic, safe="")
    request = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        method="POST",
        headers={
            "Title": title,
            "Priority": "high",
            "Tags": "chart_with_upwards_trend",
            "Content-Type": "text/plain; charset=utf-8",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        if response.status not in (200, 201):
            raise RuntimeError(f"ntfy respondió con HTTP {response.status}.")


def main() -> int:
    ntfy_topic = os.environ.get("NTFY_TOPIC", "").strip()
    if not ntfy_topic:
        raise RuntimeError("Falta el secreto NTFY_TOPIC. Añádelo en Settings > Secrets and variables > Actions.")
    if not STATE_FILE.exists():
        raise RuntimeError("No existe state.json.")

    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    if not isinstance(state.get("last_score"), (int, float)):
        raise RuntimeError("state.json no contiene un last_score numérico.")

    data = fetch_tracker()
    suri = find_suri(data)
    current = score_effort(suri)
    previous = float(state["last_score"])
    updated = str(data.get("updated") or "")
    print(f"SURI: {current:.1f}% | referencia: {previous:.1f}% | tracker: {updated}")

    if current > previous:
        send_notification(ntfy_topic, previous, current, updated)
        print(f"Notificación enviada: {previous:.1f}% -> {current:.1f}%")
    elif current < previous:
        print("El valor ha bajado; se ajusta la referencia sin notificación.")
    else:
        print("Sin subida; no se envía notificación.")

    today = datetime.now(timezone.utc).date().isoformat()
    state_changed = current != previous
    if state_changed:
        state["last_score"] = current
        state["last_tracker_update"] = updated
    if state.get("last_check_date") != today:
        state["last_check_date"] = today
        state_changed = True
    if state_changed:
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
