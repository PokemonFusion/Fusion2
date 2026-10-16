"""Durable, atomic battle-effect receipts on the owning character's Attributes."""

from __future__ import annotations

import hashlib
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
CATEGORY = "battle_rewards"
PENDING_KEY = "pending_battle_rewards"
PENDING_MESSAGE = "Your battle rewards are pending. Use +battle/retry to finish saving them."


class BufferedMessages:
    """Keep reward messages private until the corresponding transaction commits."""

    def __init__(self, target):
        """Delegate gameplay context while buffering its message methods."""
        self.target = target
        self.messages = []

    def __getattr__(self, name):
        """Preserve the existing reward helper's caller interface."""
        return getattr(self.target, name)

    def msg(self, text, **kwargs):
        """Defer character messages."""
        self.messages.append(("msg", text, kwargs))

    def log_action(self, text, **kwargs):
        """Defer battle log messages."""
        self.messages.append(("log_action", text, kwargs))

    def publish(self):
        """Publish only successfully committed rewards."""
        for method, text, kwargs in self.messages:
            send = getattr(self.target, method, None) or self.target.msg
            send(text, **kwargs)


class BattleRewards:
    """Retain immutable effect plans and claim each under the character row lock.

    Receipts use existing persistent Evennia Attributes, independent of room
    battle snapshots, so cleanup cannot erase delivery identity. The character
    row serializes both initial receipt creation and claims across processes.
    """

    def __init__(self, battle_id):
        """Require a UUID rather than a reusable numeric battle identifier."""
        self.battle_id = str(UUID(str(battle_id)))

    @staticmethod
    def character(player):
        """Resolve a production character or an integration transport wrapper."""
        return getattr(player, "character", player)

    @classmethod
    def supports(cls, player):
        """Leave nonpersistent engine simulations on their ordinary reward path."""
        character = cls.character(player)
        return bool(getattr(character, "pk", None) and getattr(character, "_meta", None)
                    and getattr(character, "attributes", None))

    def key(self, event):
        """Give one logical effect a stable bounded Attribute key."""
        return self.battle_id + ":" + hashlib.sha256(event.encode()).hexdigest()

    def _lock(self, player):
        """Lock and refresh authoritative Attributes instead of trusting handler caches."""
        from evennia.objects.models import ObjectDB

        character = ObjectDB.objects.select_for_update().get(pk=self.character(player).pk)
        character.attributes.reset_cache()
        return character

    def record(self, player, event, payload):
        """Keep the first effect plan even when a callback is replayed later."""
        from django.db import transaction

        key = self.key(event)
        with transaction.atomic():
            character = self._lock(player)
            receipt = character.attributes.get(key, category=CATEGORY)
            if receipt is None:
                character.attributes.add(key, {"battle_id": self.battle_id, "event": event,
                                               "payload": payload, "claimed": False}, category=CATEGORY)
                pending = list(character.attributes.get(PENDING_KEY, default=[]))
                character.attributes.add(PENDING_KEY, [*pending, key])
        return key

    def claim(self, player, key, *, caller=None):
        """Commit all effect writes and their receipt marker in one transaction."""
        from django.db import transaction

        from pokemon.models.core import OwnedPokemon
        from pokemon.models.stats import add_evs, add_experience, award_trainer_xp
        from pokemon.models.trainer import Trainer
        from utils.fusion import award_fusion_experience

        character = self.character(player)
        buffered = BufferedMessages(caller or player)
        try:
            with transaction.atomic():
                character = self._lock(player)
                receipt = character.attributes.get(key, category=CATEGORY)
                if not receipt or receipt["battle_id"] != self.battle_id:
                    raise ValueError("This reward receipt does not belong to this battle.")
                if receipt["claimed"]:
                    return False
                payload = receipt["payload"]
                trainer = Trainer.objects.select_for_update().get(user_id=character.pk)
                for award in sorted(payload.get("pokemon", []), key=lambda row: row["id"]):
                    mon = OwnedPokemon.objects.select_for_update().get(pk=award["id"], trainer=trainer)
                    add_experience(mon, award["exp"], caller=buffered)
                    add_evs(mon, award["evs"])
                    mon.save()
                    award_fusion_experience(player, mon, award["exp"])
                    if award.get("message"):
                        buffered.log_action(award["message"])
                if payload.get("txp"):
                    award_trainer_xp(player, payload["txp"], caller=buffered)
                if payload.get("money"):
                    trainer.add_money(payload["money"])
                # Replacing the whole detached mapping avoids mutating an
                # autosaving SaverDict before the transaction is complete.
                character.attributes.add(key, {**dict(receipt), "claimed": True}, category=CATEGORY)
                pending = list(character.attributes.get(PENDING_KEY, default=[]))
                character.attributes.add(PENDING_KEY, [entry for entry in pending if entry != key])
                transaction.on_commit(buffered.publish, robust=True)
                # Keep the existing character's trainer view consistent only
                # after SQL commits; rollback must never leak a paid wallet.
                if getattr(player, "trainer", None) is not None:
                    transaction.on_commit(player.trainer.refresh_from_db, robust=True)
            return True
        except Exception:
            character.attributes.reset_cache()
            raise

    def deliver(self, player, event, payload, *, caller=None, before_claim=None):
        """Retain failed claims while allowing a recorded battle effect to finish."""
        key = self.record(player, event, payload)
        if before_claim is not None:
            before_claim()
        try:
            return self.claim(player, key, caller=caller)
        except Exception:
            logger.exception("Battle reward delivery is pending for %s", key)
            player.msg(PENDING_MESSAGE)
            return None

    def retry(self, player, *, caller=None):
        """Claim this battle's pending effects and leave failures visible."""
        for key in self.pending(player):
            if key.startswith(self.battle_id + ":"):
                self.claim(player, key, caller=caller)

    @classmethod
    def pending(cls, player):
        """Read the bounded pending index without loading completed receipt history."""
        character = cls.character(player)
        character.attributes.reset_cache()
        return list(character.attributes.get(PENDING_KEY, default=[]))

    @staticmethod
    def faint_plan(player, exp, evs, txp, participants):
        """Freeze the existing EXP Share and held-item rules before delivery."""
        from pokemon.models.stats import (
            _format_reward_message,
            _is_fainted,
            _resolve_participants,
            apply_item_ev_mod,
            apply_item_exp_mod,
        )
        from utils.fusion import get_battle_party_with_fusion

        mons = get_battle_party_with_fusion(player, player.storage.get_party())
        participating = _resolve_participants(mons, participants)
        if not participating and exp:
            participating = next(([mon] for mon in mons if not _is_fainted(mon)), [])
        shares = []
        if participating:
            amount, remainder = divmod(exp, len(participating))
            shares.extend((mon, amount + (index < remainder)) for index, mon in enumerate(participating))
        if getattr(player.db, "exp_share", False):
            shared = (exp // max(len(participating) or len(mons), 1)) // 2
            shares.extend((mon, shared) for mon in mons if mon not in participating and not _is_fainted(mon))
        awards = []
        for mon, amount in shares:
            gained = apply_item_exp_mod(mon, amount)
            gained_evs = apply_item_ev_mod(mon, evs)
            awards.append({"id": str(mon.pk), "exp": gained, "evs": gained_evs,
                           "message": _format_reward_message(mon, gained, gained_evs)})
        return {"pokemon": awards, "txp": txp}
