#!/usr/bin/env python3
"""Watch SURI's PortWatch score, FPS and the public race leader; notify via ntfy."""

# Polling workflow refresh: keep the scheduled monitor active.
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
    """Match JavaScript Math.round(value * 10) / 10."""
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

    stability_raw = gta.get("stability")
    if isinstance(stability_raw, (int, float)) and math.isfinite(float(stability_raw)):
        stability = clamp01(stability_raw)
    else:
        stability = STABILITY_VALUES.get(str(stability_raw or "unknown"), 0.0)

    tracks = {
        "story": clamp01(gta.get("story")),
        "render": clamp01(gta.get("render")),
        "perf": clamp01((float(gta.get("fps") or 0.0)) / 30.0),
        "stability": stability,
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


def find_leader(data: dict) -> dict | None:
    """Match PortWatch overall(): every non-nuked effort participates."""
    ranked = [
        effort for effort in data.get("efforts", [])
        if isinstance(effort, dict) and not effort.get("nuked")
    ]
    if not ranked:
        return None

    def stars(effort: dict) -> float:
        try:
            return float((effort.get("stats") or {}).get("stars") or 0)
        except (TypeError, ValueError):
            return 0.0

    # PortWatch overall() ranks all non-nuked efforts by score, then stars.
    ranked.sort(key=lambda effort: (score_effort(effort), stars(effort)), reverse=True)
    return ranked[0]

def format_number(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}".replace(".", ",")


def send_notification(
    topic: str,
    current: float,
    fps: float,
    leader_name: str,
) -> None:
    topic = topic.strip()
    if not topic:
        raise RuntimeError("Falta el secreto NTFY_TOPIC en GitHub Actions.")

    current_text = format_number(current)
    if not math.isfinite(fps) or fps <= 0:
        fps_text = "—"
    elif fps.is_integer():
        fps_text = str(int(fps))
    else:
        fps_text = format_number(fps)

    leader_name = (leader_name or "—").strip()
    title = "Progreso GTAVI"
    message = f"{current_text} % ⚡ {fps_text} FPS | {leader_name}"

    url = "https://ntfy.sh/" + urllib.parse.quote(topic, safe="")
    request = urllib.request.Request(
        url,
        data=message.encode("utf-8"),
        method="POST",
        headers={
            "Title": title,
            "Priority": "high",
            "Click": PAGE_URL,
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

    gta = suri.get("gta") or {}
    fps = round_one_decimal(float(gta.get("fps") or 0.0))
    leader = find_leader(data)
    leader_name = str((leader or {}).get("name") or (leader or {}).get("id") or "—")

    score_increased = current > previous

    print(
        f"SURI: {current:.1f}% | FPS: {fps:g} | líder público: {leader_name} "
        f"| referencia: {previous:.1f}% | tracker: {updated}"
    )

    # Only notify when SURI's percentage increases. FPS and leader are
    # refreshed in state.json below without generating separate notifications.
    if score_increased:
        send_notification(ntfy_topic, current, fps, leader_name)
        print("Notificación enviada: ha aumentado el porcentaje de SURI.")
    elif current < previous:
        print("El porcentaje bajó; se actualiza la referencia sin avisar.")
    else:
        print("El porcentaje no ha subido; no se envía notificación.")

    today = datetime.now(timezone.utc).date().isoformat()
    new_values = {
        "last_score": current,
        "last_fps": fps,
        "last_leader": leader_name,
        "last_tracker_update": updated,
        "last_check_date": today,
    }
    state_changed = any(state.get(key) != value for key, value in new_values.items())
    if state_changed:
        state.update(new_values)
        STATE_FILE.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
