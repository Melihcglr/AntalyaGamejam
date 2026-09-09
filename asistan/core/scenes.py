from __future__ import annotations

from typing import Any, Callable

from .hands import ActionResult
from .iot_models import SceneSpec, SceneStep


ExecuteFn = Callable[[dict[str, Any]], ActionResult]


class SceneRunner:
    def __init__(self, scenes: dict[str, SceneSpec]):
        self.scenes = {k.lower(): v for k, v in scenes.items()}

    def resolve(self, name: str) -> tuple[str, SceneSpec] | None:
        q = name.lower().strip()
        if q in self.scenes:
            return q, self.scenes[q]
        for key, spec in self.scenes.items():
            aliases = [a.lower() for a in spec.aliases] + [key, (spec.name or "").lower()]
            # "oyun modu" / "oyun"
            if q in aliases:
                return key, spec
            if any(a and (a in q or q in a) for a in aliases):
                return key, spec
        return None

    def list_scenes(self) -> ActionResult:
        data = {
            k: {
                "name": v.name or k,
                "aliases": v.aliases,
                "steps": [s.model_dump() for s in v.steps],
            }
            for k, v in self.scenes.items()
        }
        return ActionResult(True, "Kayıtlı sahneler", data={"scenes": data})

    def run(self, name: str, execute: ExecuteFn) -> ActionResult:
        found = self.resolve(name)
        if not found:
            return ActionResult(False, f"Sahne yok: {name}")
        key, spec = found
        results: list[dict[str, Any]] = []
        for step in spec.steps:
            action = self._step_to_action(step)
            result = execute(action)
            results.append(
                {
                    "action": action,
                    "ok": result.ok,
                    "message": result.message,
                }
            )
            if not result.ok and not result.needs_confirm:
                return ActionResult(
                    False,
                    f"{spec.name or key} yarım kaldı: {result.message}",
                    data={"scene": key, "results": results},
                )
        ok_n = sum(1 for r in results if r["ok"])
        return ActionResult(
            True,
            f"{spec.name or key} aktif ({ok_n}/{len(results)} adım).",
            data={"scene": key, "results": results},
        )

    def _step_to_action(self, step: SceneStep) -> dict[str, Any]:
        kind = step.type.lower().strip()
        if kind == "device":
            return {
                "type": "device",
                "target": step.target,
                "state": step.state or "toggle",
                "confirm_token": step.confirm_token,
            }
        return {
            "type": kind,
            "target": step.target,
            "monitor": step.monitor,
            "confirm_token": step.confirm_token,
            "state": step.state,
        }
