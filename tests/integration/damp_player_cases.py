"""Native Damp weather/prevention through normal persistent player battle commands."""

from battle_player_fixtures import BattlePlayerFixture, run


class DampPlayerCases(BattlePlayerFixture):
    """Check actual native sources, PP, residual HP and saved/rebuilt effects."""

    def test_native_weather_and_pending_rebuild(self):
        """Wooper stays immune to sand; Mew pays Sandstorm PP and takes residual chip."""
        from pokemon.models.core import OwnedPokemon

        wooper = self.add(0, "Wooper", ["Water Gun", "Tail Whip"], ability="Damp", slot=3)
        mew = self.add(1, "Mew", ["Sandstorm", "Safeguard"], ability="Synchronize", slot=4)
        self.launch()
        before = self.snapshot()
        self.turn("Tail Whip", "Sandstorm", rebuild=True)
        part_a, part_b = self.session.battle.participants
        original = next(row for row in before["owned"] if row["unique_id"] == wooper.pk)
        self.assertEqual(part_a.active[0].hp, original["current_hp"])
        self.assertEqual(OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=mew.pk),
                         part_b.active[0].max_hp - part_b.active[0].max_hp // 16)
        self.assertEqual(OwnedPokemon.objects.values_list("ability", flat=True).get(pk=wooper.pk), "Damp")
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.services.pp_capacity import PPCapacity
        self.assertEqual(ActiveMoveslot.objects.get(pokemon=mew, slot=1).current_pp,
                         PPCapacity.for_move("Sandstorm").base - 1)
        self.rebuild()
        self.turn("Tail Whip", "Safeguard")

    def explosive(self, move):
        """A failed explosive attempt must not faint its user or damage native Damp."""
        self.add(0, "Wooper", ["Tail Whip"], ability="Damp")
        mew = self.add(1, "Mew", [move], ability="Synchronize")
        self.launch()
        before = [p.active[0].hp for p in self.session.battle.participants]
        self.turn("Tail Whip", move)
        self.assertEqual([p.active[0].hp for p in self.session.battle.participants], before)
        from pokemon.models.moves import ActiveMoveslot
        from pokemon.services.pp_capacity import PPCapacity
        slot = ActiveMoveslot.objects.get(pokemon=mew, slot=1)
        self.assertEqual(slot.current_pp, PPCapacity.for_move(move).base - 1)

    def test_explosion(self):
        """The normal Explosion command preserves both combatants."""
        self.explosive("Explosion")

    def test_selfdestruct(self):
        """The normal Self-Destruct command preserves both combatants."""
        self.explosive("Self-Destruct")

    def test_native_aftermath_contact_ko(self):
        """A real contact KO on native Aftermath cannot damage the native Damp attacker."""
        from pokemon.models.core import OwnedPokemon
        from battle_player_fixtures import EVIDENCE

        quagsire = self.add(0, "Quagsire", ["Waterfall"], ability="Damp", level=100)
        drifloon = self.add(1, "Drifloon", ["Focus Energy"], ability="Aftermath")
        self.add(1, "Magikarp", ["Splash"], ability="Swift Swim")
        OwnedPokemon.objects.filter(pk=drifloon.pk).update(current_hp=1)
        drifloon.refresh_from_db()
        EVIDENCE.append({"case": self.id(), "label": "separate-hp1-ko-prerequisite", "after": self.snapshot()})
        self.launch()
        before = OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=quagsire.pk)
        self.turn("Waterfall", "Focus Energy")
        self.assertEqual(OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=drifloon.pk), 0)
        self.assertEqual(OwnedPokemon.objects.values_list("current_hp", flat=True).get(pk=quagsire.pk), before)
        self.rebuild()


if __name__ == "__main__":
    run(DampPlayerCases)
