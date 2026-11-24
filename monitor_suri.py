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


def track_step(value: object, steps: list[tuple[float, str]]) -> str:
    number = clamp01(value)
    eligible = [label for threshold, label in steps if number >= threshold]
    return eligible[-1] if eligible else steps[0][1]


def format_tracker_time(value: str) -> str:
    if not value:
        return "Sin fecha indicada"
    try:
        moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return moment.astimezone().strftime("%d/%m/%Y · %H:%M")
    except ValueError:
        return value


def send_notification(
    topic: str,
    previous: float,
    current: float,
    updated: str,
    effort: dict,
) -> None:
    topic = topic.strip()
    if not topic:
        raise RuntimeError("Falta el secreto NTFY_TOPIC en GitHub Actions.")

    gta = effort.get("gta") or {}
    delta = round_one_decimal(current - previous)
    current_text = f"{current:.1f}".replace(".", ",")
    previous_text = f"{previous:.1f}".replace(".", ",")
    delta_text = f"{delta:.1f}".replace(".", ",")

    filled = max(0, min(20, int(round(current / 5))))
    progress_bar = "█" * filled + "░" * (20 - filled)

    if ladder_value(gta.get("playable")) >= 1:
        milestone = "Jugable · personaje controlable"
    elif ladder_value(gta.get("world")) >= 1:
        milestone = "En el mundo · historia cargada"
    elif ladder_value(gta.get("menu")) >= 1:
        milestone = "Menú principal"
    elif ladder_value(gta.get("boots")) >= 1:
        milestone = "Primer fotograma"
    elif ladder_value(gta.get("loads")) >= 1:
        milestone = "Ejecutable en marcha"
    else:
        milestone = "Trabajo de base"

    story = track_step(gta.get("story"), [
        (0.0, "Atrapado en la apertura"),
        (0.1, "Prólogo superado"),
        (0.25, "Primeras misiones"),
        (0.4, "Primer acto"),
        (0.6, "Mitad de la historia"),
        (0.85, "Historia principal completada"),
        (1.0, "Juego completado al 100%"),
    ])
    rendering = track_step(gta.get("render"), [
        (0.0, "Imagen negra o rota"),
        (0.25, "Formas dibujadas, iluminación incompleta"),
        (0.5, "Iluminación presente, efectos pendientes"),
        (0.75, "Casi como consola, con fallos menores"),
        (1.0, "Imagen equivalente a consola"),
    ])
    stability = {
        "unknown": "Sin datos",
        "constant": "Se cierra constantemente",
        "often": "Fallos frecuentes",
        "sometimes": "Fallos ocasionales",
        "rarely": "Pocos fallos",
        "stable": "Estable",
    }.get(str(gta.get("stability") or "unknown"), "Sin datos")

    fps = float(gta.get("fps") or 0.0)
    fps_text = f"{fps:g} FPS reportados" if fps > 0 else "Sin medición disponible"
    updated_text = format_tracker_time(updated)

    title = f"SURI +{delta_text} -> {current_text}%"
    message = f"""# 🚀 SURI HA AVANZADO

## {current_text} %

> 📈 **+{delta_text} puntos** desde la última comprobación.

---

### 📊 PROGRESO PORTWATCH

**{progress_bar}**

**{current_text} / 100 puntos**

### 🎮 ESTADO DEL PROYECTO

- **Hito:** {milestone}
- **Rendimiento:** {fps_text}
- **Renderizado:** {rendering}
- **Historia:** {story}
- **Estabilidad:** {stability}

---

### 🧭 DETALLES DEL CAMBIO

- Antes: **{previous_text}%**
- Ahora: **{current_text}%**
- Incremento: **+{delta_text} puntos porcentuales**
- Datos publicados: *{updated_text}*

[🔎 Abrir ficha de SURI en PortWatch](https://portwatch-vi.xyz/#effort-suri)

---

*Fuente: PortWatch VI · Monitor automático*

> Esta cifra es la puntuación de progreso de PortWatch, no el porcentaje literal de juego terminado. Se avisa de cualquier subida publicada, incluso de una décima.
"""

    url = "https://ntfy.sh/" + urllib.parse.quote(topic, safe="")
    icon_url = (
        "https://raw.githubusercontent.com/Manolilloo/suri-progress-alert/"
        "main/assets/suri-notification-icon.png?v=28633272"
    )
    actions = (
        f"view, Abrir ficha, {PAGE_URL}, clear=true; "
        f"copy, Copiar porcentaje, {current:.1f}%; "
        "view, Metodologia, https://portwatch-vi.xyz/#method"
    )
    request = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        method="POST",
        headers={
            "Title": title,
            "Priority": "high",
            "Tags": "rocket,chart_with_upwards_trend,video_game",
            "Icon": icon_url,
            "Click": PAGE_URL,
            "Actions": actions,
            "Markdown": "yes",
            "Content-Type": "text/markdown",
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
        send_notification(ntfy_topic, previous, current, updated, suri)
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
