"""Adapter applying battle results to persistent models."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Iterable, Mapping

from django.db import transaction

from pokemon.models.core import OwnedPokemon
from pokemon.models.moves import ActiveMoveslot
from pokemon.models.stats import (
    add_evs,
    add_experience,
    apply_item_ev_mod,
    award_experience_to_party,
)
from pokemon.models.trainer import Trainer
from utils.locks import clear_battle_lock


class CommitAdapter:
    """Commit post-battle changes back to persistent models."""

    @staticmethod
    def _apply_mon_updates(mon: OwnedPokemon, data: Mapping[str, Any]) -> None:
        if "current_hp" in data:
            mon.current_hp = data["current_hp"]
        if "status" in data:
            mon.status = data["status"]
        if "friendship" in data:
            mon.friendship = data["friendship"]
        if "held_item" in data:
            mon.held_item = data["held_item"]
        for mv in data.get("moves", []):
            slot = mv.get("slot")
            pp = mv.get("current_pp")
            if slot is None or pp is None:
                continue
            ActiveMoveslot.objects.filter(pokemon=mon, slot=slot).update(current_pp=pp)
        mon.save()

    @staticmethod
    def _capture(trainer: Trainer | None, spec: Mapping[str, Any], character=None):
        """Use the same durable encounter claim as in-battle capture."""
        if trainer is None or character is None:
            raise ValueError("Capture requires a character and its owning trainer.")
        from pokemon.services.capture import finalize_wild_capture

        target = SimpleNamespace(
            model_id=spec.get("model_id") or spec.get("encounter_ref"),
            hp=spec.get("current_hp", 0),
        )
        # Preserve absence versus explicit removal for the shared capture service.
        for field in ("item", "held_item"):
            if field in spec:
                setattr(target, field, spec[field])
        return finalize_wild_capture(
            target_poke=target,
            player=character, trainer=trainer, ball_name=spec.get("ball_name", ""),
        )

    @classmethod
    def apply(cls, participants: Iterable[Mapping[str, Any]]) -> None:
        participants = list(participants)
        with transaction.atomic():
            # Claim captures before taking party Pokemon row locks. Sort owners
            # so a multi-participant commit follows the same storage lock order.
            captures = [part for part in participants if part.get("capture")]
            captures.sort(key=lambda part: getattr(getattr(part.get("character"), "storage", None), "pk", 0) or 0)
            for part in captures:
                character = part.get("character")
                cls._capture(getattr(character, "trainer", None), part["capture"], character)
            for part in participants:
                char = part.get("character")
                trainer = getattr(char, "trainer", None)
                for pmon in part.get("party", []):
                    uid = pmon.get("unique_id")
                    if not uid:
                        continue
                    mon = OwnedPokemon.objects.filter(unique_id=uid).first()
                    if not mon:
                        continue
                    cls._apply_mon_updates(mon, pmon)
                    if "exp" in pmon:
                        add_experience(mon, int(pmon["exp"]))
                    if "evs" in pmon:
                        add_evs(mon, apply_item_ev_mod(mon, pmon["evs"]))
                exp = part.get("exp")
                if exp:
                    award_experience_to_party(char, int(exp), part.get("evs"))
                if trainer and hasattr(trainer, "add_money"):
                    money = part.get("money")
                    if money:
                        try:
                            trainer.add_money(int(money))
                        except Exception:
                            pass
                if trainer and hasattr(trainer, "add_badge"):
                    for badge in part.get("badges", []):
                        try:
                            trainer.add_badge(badge)
                        except Exception:
                            pass
                if char:
                    try:
                        clear_battle_lock(char)
                    except Exception:
                        pass


__all__ = ["CommitAdapter"]
