"""Adapter applying battle results to persistent models."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from django.db import transaction

from pokemon.models.core import OwnedPokemon
from pokemon.models.moves import ActiveMoveslot, Move, Moveset, MovesetSlot
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
    def _capture(trainer: Trainer | None, spec: Mapping[str, Any]) -> OwnedPokemon:
        mon = OwnedPokemon.objects.create(
            trainer=trainer if isinstance(trainer, Trainer) else None,
            species=spec.get("species", ""),
            level=spec.get("level", 1),
            ability=spec.get("ability", ""),
            nature=spec.get("nature", ""),
            gender=spec.get("gender", ""),
            ivs=spec.get("ivs", [0, 0, 0, 0, 0, 0]),
            evs=spec.get("evs", [0, 0, 0, 0, 0, 0]),
            held_item=spec.get("held_item", ""),
            current_hp=spec.get("current_hp", 0),
            friendship=spec.get("friendship", 0),
            is_shiny=bool(spec.get("is_shiny", False)),
            tera_type=spec.get("tera_type", ""),
            flags=list(spec.get("flags", []) or []),
        )
        moveset = Moveset.objects.create(pokemon=mon, index=0)
        for idx, mv in enumerate(spec.get("moves", []), start=1):
            name = mv.get("name")
            if not name:
                continue
            move_obj, _ = Move.objects.get_or_create(name=name)
            MovesetSlot.objects.create(moveset=moveset, move=move_obj, slot=idx)
            ActiveMoveslot.objects.create(
                pokemon=mon, move=move_obj, slot=idx, current_pp=mv.get("current_pp")
            )
        mon.active_moveset = moveset
        mon.save()
        return mon

    @classmethod
    def apply(cls, participants: Iterable[Mapping[str, Any]]) -> None:
        with transaction.atomic():
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
                cap = part.get("capture")
                if cap:
                    cls._capture(trainer if isinstance(trainer, Trainer) else None, cap)
                if char:
                    try:
                        clear_battle_lock(char)
                    except Exception:
                        pass


__all__ = ["CommitAdapter"]
