"""Ordinary reviewed Mirror Herb teaching, exact slot/PP preservation and SQL races."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import os
from pathlib import Path
from threading import Barrier
import unittest
from unittest.mock import patch
from uuid import uuid4

from battle_player_fixtures import BattlePlayerFixture, EVIDENCE
from isolated_postgres import IsolatedPostgres


class MirrorHerbCases(BattlePlayerFixture):
    """Keep donor acquisition/preparation separate from the actual ordinary teaching flow."""

    def setUp(self):
        """Prepare an evolved native recipient, unrelated legal donor and real held Herb."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.moves import ActiveMoveslot
        from commands.player.cmd_party import CmdSetHoldItem

        super().setUp()
        self.room.db.is_daycare = True
        ObjectDB.objects.filter(pk=self.players[0].pk).update(db_location_id=self.room.pk)
        self.recipient = self.add(0, "Umbreon", ["Tackle"], slot=3)
        self.donor = self.add(0, "Jirachi", ["Wish"], slot=6)
        ActiveMoveslot.objects.filter(pokemon=self.recipient).update(current_pp=1)
        ActiveMoveslot.objects.filter(pokemon=self.donor).update(current_pp=0)
        self.players[0].trainer.add_item("Mirror Herb", 1)
        command = CmdSetHoldItem()
        command.caller, command.args = self.players[0], "3=Mirror Herb"
        command.parse()
        command.func()

    def snapshot(self):
        """Include all saved move knowledge/sets, money and normal owned resources."""
        from pokemon.models.moves import PokemonLearnedMove, MovesetSlot
        from pokemon.models.trainer import Trainer

        result = super().snapshot()
        identifiers = [row["unique_id"] for row in result["owned"]]
        result.update(knowledge=list(PokemonLearnedMove.objects.filter(pokemon_id__in=identifiers)
                      .order_by("pk").values()),
                      stored=list(MovesetSlot.objects.filter(moveset__pokemon_id__in=identifiers)
                      .order_by("pk").values()),
                      wallets=list(Trainer.objects.filter(pk__in=[p.trainer.pk for p in self.players])
                      .order_by("pk").values_list("money", flat=True)))
        return result

    def cmd(self, args):
        """Use the shipped Daycare command parser and capture committed output/state."""
        from commands.player.cmd_daycare import CmdDaycare

        before, offset = self.snapshot(), len(self.players[0].messages)
        command = CmdDaycare()
        command.caller, command.args = self.players[0], args
        command.parse()
        command.func()
        messages = self.players[0].messages[offset:]
        EVIDENCE.append({"label": "ordinary-mirror-herb-command", "command": "+daycare " + args,
                         "before": before, "after": self.snapshot(), "messages": messages})
        return "\n".join(map(str, messages))

    def service(self):
        """Use fresh current ownership, stored confirmation and the actual teaching service."""
        from pokemon.services.mirror_herb import MirrorHerbTeaching

        return MirrorHerbTeaching(self.players[0])

    def review(self):
        """Choose one explicit exact move rather than copying or replacing the whole moveset."""
        self.assertIn("Review:", self.cmd("herb 3=6/Wish"))
        return self.service().token()

    def test_review_confirm_zero_pp_donor_reconnect_and_no_replay(self):
        """One new learned/active/saved move preserves every prior PP and all other resources."""
        from django.db import connection
        from pokemon.models.moves import ActiveMoveslot, MovesetSlot, PokemonLearnedMove

        before = self.snapshot()
        self.review()
        self.assertEqual(self.snapshot(), before)
        connection.close()
        self.players[0].attributes.reset_cache()
        self.assertIn("learned Wish", self.cmd("herb confirm"))
        after = self.snapshot()
        self.assertEqual(after["owned"], before["owned"])
        self.assertEqual(after["bags"], before["bags"])
        self.assertEqual(after["wallets"], before["wallets"])
        prior_ids = {row["id"] for row in before["moves"]}
        self.assertEqual([row for row in after["moves"] if row["id"] in prior_ids], before["moves"])
        self.assertEqual(PokemonLearnedMove.objects.filter(pokemon=self.recipient, move__name="Wish").count(), 1)
        slot = ActiveMoveslot.objects.get(pokemon=self.recipient, move__name="Wish")
        self.assertEqual((slot.slot, slot.current_pp), (2, 10))
        self.assertTrue(MovesetSlot.objects.filter(moveset=self.recipient.active_moveset, slot=2, move=slot.move).exists())
        self.assertIn("already saved", self.cmd("herb confirm"))
        self.assertEqual(self.snapshot(), after)
        self.assertIn("already knows", self.cmd("herb 3=6/Wish"))
        self.assertEqual(self.snapshot(), after)

    def test_stale_item_move_pp_native_and_room_refuse_without_overwrite(self):
        """Every confirmation is bound to current physical item, exact metadata and move view."""
        from evennia.objects.models import ObjectDB
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.moves import ActiveMoveslot

        for kind in ("item", "pp", "species", "room"):
            self.review()
            if kind == "item":
                OwnedPokemon.objects.filter(pk=self.recipient.pk).update(held_item="")
            elif kind == "pp":
                ActiveMoveslot.objects.filter(pokemon=self.donor).update(current_pp=1)
            elif kind == "species":
                OwnedPokemon.objects.filter(pk=self.recipient.pk).update(species="Espeon")
            else:
                ObjectDB.objects.filter(pk=self.players[0].pk).update(db_location_id=None)
            before = self.snapshot()
            self.cmd("herb confirm")
            self.assertEqual(self.snapshot(), before)
            OwnedPokemon.objects.filter(pk=self.recipient.pk).update(held_item="Mirror Herb", species="Umbreon")
            ActiveMoveslot.objects.filter(pokemon=self.donor).update(current_pp=0)
            ObjectDB.objects.filter(pk=self.players[0].pk).update(db_location_id=self.room.pk)

    def test_egg_foreign_reservation_fusion_battle_and_non_egg_move_guards(self):
        """Teaching never borrows another owner, inactive source or non-native move permission."""
        from pokemon.models.core import OwnedPokemon
        from pokemon.services.ownership import PokemonReservations
        from pokemon.services.placement import PlacementService

        for mon in (self.recipient, self.donor):
            for key, value in (("is_egg", True), ("trainer_id", self.players[1].trainer.pk)):
                old = OwnedPokemon.objects.values_list(key, flat=True).get(pk=mon.pk)
                OwnedPokemon.objects.filter(pk=mon.pk).update(**{key: value})
                before = self.snapshot()
                self.cmd("herb 3=6/Wish")
                self.assertEqual(self.snapshot(), before)
                self.assertIsNone(self.service().read())
                OwnedPokemon.objects.filter(pk=mon.pk).update(**{key: old})
        for query in ("herb 3=3/Wish", "herb 3=6/Tackle", "herb 3=6/Not a move", "herb 3=6/Wis"):
            before = self.snapshot()
            self.cmd(query)
            self.assertEqual(self.snapshot(), before)
            self.assertIsNone(self.service().read())
        token = uuid4()
        reservations = PokemonReservations(self.players[0])
        reservations.claim("market", [self.donor.pk], token)
        self.cmd("herb 3=6/Wish")
        self.assertIsNone(self.service().read())
        reservations.release("market", token)
        PlacementService(self.players[0].storage).reserve_for_fusion(self.recipient)
        self.players[0].character.db.fusion_id = str(self.recipient.pk)
        self.cmd("herb fusion=6/Wish")
        self.assertIsNone(self.service().read())
        PlacementService(self.players[0].storage).return_from_fusion(self.recipient, preferred_slot=3)
        self.players[0].character.db.fusion_id = None
        self.players[0].character.db.battle_lock = "herb-fixture-battle"
        self.cmd("herb 3=6/Wish")
        self.assertIsNone(self.service().read())
        self.players[0].character.db.battle_lock = None
        self.review()

    def test_expiry_cancel_full_slot_and_existing_inactive_knowledge(self):
        """No expiry, cancelled review, full set or historical knowledge can refresh PP."""
        from django.utils import timezone
        from pokemon.models.moves import ActiveMoveslot, Move, MovesetSlot, PokemonLearnedMove

        self.review()
        later = timezone.now() + timedelta(seconds=301)
        before = self.snapshot()
        with patch("pokemon.services.mirror_herb.timezone.now", return_value=later):
            self.assertIn("expired", self.cmd("herb confirm"))
        self.assertEqual(self.snapshot(), before)
        self.cmd("herb cancel")
        self.assertIsNone(self.service().read())
        self.cmd("herb confirm")
        self.assertEqual(self.snapshot(), before)
        wish = Move.objects.get(name="Wish")
        PokemonLearnedMove.objects.create(pokemon=self.recipient, move=wish)
        before = self.snapshot()
        self.assertIn("already knows", self.cmd("herb 3=6/Wish"))
        self.assertEqual(self.snapshot(), before)
        PokemonLearnedMove.objects.filter(pokemon=self.recipient, move=wish).delete()
        for slot, name in enumerate(("Sand Attack", "Quick Attack", "Swift"), 2):
            move, _ = Move.objects.get_or_create(name=name)
            MovesetSlot.objects.create(moveset=self.recipient.active_moveset, slot=slot, move=move)
            ActiveMoveslot.objects.create(pokemon=self.recipient, slot=slot, move=move, current_pp=1)
        before = self.snapshot()
        self.assertIn("empty active slot", self.cmd("herb 3=6/Wish"))
        self.assertEqual(self.snapshot(), before)

    def test_real_post_write_rollback_and_concurrent_confirmation(self):
        """All three new move rows and the receipt roll back, then one confirmation can win."""
        from django.db import connections
        from pokemon.models.moves import ActiveMoveslot

        expected = self.review()
        before, selection, original = self.snapshot(), self.service().read(), ActiveMoveslot.save

        def fail_after_write(slot, *args, **kwargs):
            value = original(slot, *args, **kwargs)
            if slot.pokemon_id == self.recipient.pk and slot.slot == 2:
                raise RuntimeError("Herb post-active-slot fixture refusal")
            return value

        with patch.object(ActiveMoveslot, "save", fail_after_write), self.assertRaises(RuntimeError):
            self.cmd("herb confirm")
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(self.service().read(), selection)
        barrier = Barrier(2)

        def claim():
            connections.close_all()
            try:
                barrier.wait(timeout=10)
                return self.service().confirm(expected=expected)["changed"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(lambda _: claim(), range(2)))
        self.assertEqual(results.count(True), 1)
        self.assertEqual(ActiveMoveslot.objects.filter(pokemon=self.recipient, move__name="Wish").count(), 1)

    def test_taught_move_is_usable_after_checkpoint_restore_and_keeps_herb(self):
        """Use the new move in an ordinary PvP turn without refreshing prior PP or copying battle boosts."""
        from pokemon.models.moves import ActiveMoveslot

        self.review()
        self.cmd("herb confirm")
        self.add(1, "Mew", ["Pound"], slot=3)
        self.launch()
        self.turn("A1 Wish A1", "B1 Pound A1", rebuild=True)
        ours = self.session.battle.participants[0].active[0]
        self.assertEqual(next(move.pp for move in ours.moves if move.name == "Wish"), 9)
        self.session.end()
        self.session = None
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.recipient, move__name="Wish").current_pp, 9)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.recipient, move__name="Tackle").current_pp, 1)
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=self.donor, move__name="Wish").current_pp, 0)

    def test_explicit_public_daycare_travel_and_teaching(self):
        """Author one source explicitly, traverse its public exit and teach through ordinary inputs."""
        from django.contrib.contenttypes.models import ContentType
        from evennia.objects.models import ObjectDB
        from evennia.utils.create import create_object
        from pokemon.services.daycare_teaching_location import MIRROR_HERB_DAYCARE

        ContentType.objects.get_for_model(ObjectDB)
        hub = create_object("typeclasses.rooms.FusionRoom", key="Daycare acceptance hub", nohome=True)
        route = MIRROR_HERB_DAYCARE
        room = route.install(hub)
        self.assertEqual(route.install(hub).pk, room.pk)
        owner = self.players[0].character
        owner.move_to(hub, quiet=True)
        entrance = ObjectDB.objects.get(db_location=hub, db_destination=room)
        self.assertTrue(entrance.access(owner, "call", no_superuser_bypass=True))
        self.assertTrue(entrance.access(owner, "traverse"))

        def move(destination, **kwargs):
            value = owner.move_to(destination, quiet=True, move_hooks=False)
            if value:
                self.players[0].location = destination
            return value

        self.players[0].move_to = move
        command = entrance.exit_command()
        command.caller, command.obj, command.args = self.players[0], entrance, ""
        command.func()
        self.assertEqual(ObjectDB.objects.values_list("db_location_id", flat=True).get(pk=owner.pk), room.pk)
        self.review()
        self.assertIn("learned Wish", self.cmd("herb confirm"))


if __name__ == "__main__":
    from ordinary_player_fixtures import OrdinaryPlayerFixtures
    from isolated_battle_logs import IsolatedBattleLogs
    try:
        with IsolatedPostgres() as database:
            database.create_model_tables()
            with OrdinaryPlayerFixtures("mirror-herb"), IsolatedBattleLogs():
                result = unittest.TextTestRunner(verbosity=2).run(
                    unittest.defaultTestLoader.loadTestsFromTestCase(MirrorHerbCases))
    finally:
        if os.environ.get("PF2_MIRROR_HERB_EVIDENCE"):
            Path(os.environ["PF2_MIRROR_HERB_EVIDENCE"]).write_text(
                json.dumps(EVIDENCE, indent=2, default=str) + "\n", encoding="utf-8")
    raise SystemExit(not result.wasSuccessful())
