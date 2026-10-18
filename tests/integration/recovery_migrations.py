"""Rehearse fresh installs and both upgrade paths in disposable PostgreSQL schemas.

Run only with operational approval: this deliberately applies migrations, but
only inside the schema protected by IsolatedPostgres. An explicit
PF2_TEST_POSTGRES_DSN is required. Each scenario runs in a fresh subprocess.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from isolated_postgres import IsolatedPostgres

BASELINES = {
    "adventure": "0040_adventure_participation",
    "main": "0041_placement_integrity_triggers",
    "status": "0043_gym_victory",
    "strategy_gym": "0044_owned_pokemon_status",
}


class RecoveryMigrationRehearsal:
    """Preserve real progression and placement data across the merged history."""

    def __init__(self, scenario):
        self.scenario = scenario

    def run(self):
        """Apply migrations only after establishing a guarded disposable schema."""
        from django.apps import apps
        from django.db import connection
        from django.db.migrations.autodetector import MigrationAutodetector
        from django.db.migrations.executor import MigrationExecutor
        from django.db.migrations.state import ProjectState

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        if self.scenario in BASELINES:
            baseline = [("pokemon", BASELINES[self.scenario])]
            executor.migrate(baseline)
            seed = self.seed_progression(executor.loader.project_state(baseline).apps)
        else:
            seed = None
        executor = MigrationExecutor(connection)
        executor.migrate(targets)
        executor = MigrationExecutor(connection)
        assert not executor.migration_plan(targets), "Migrations did not reach every graph leaf."
        required = {("pokemon", name) for name in (
            "0040_adventure_participation", "0041_placement_integrity_triggers",
            "0042_merge_adventure_placement", "0043_gym_victory",
            "0044_owned_pokemon_status",
            "0045_production_strategy_gym",
        )}
        assert required <= set(executor.loader.applied_migrations), "Merged migration history is incomplete."
        changes = MigrationAutodetector(
            executor.loader.project_state(), ProjectState.from_apps(apps),
        ).changes(graph=executor.loader.graph, trim_to_apps={"pokemon"})
        assert not changes, f"Pokemon model state drift: {changes}"
        if seed is None:
            seed = self.seed_progression(executor.loader.project_state(targets).apps)
        self.verify_progression(seed)
        print(f"Migration rehearsal {self.scenario}: passed; data preserved, no model drift.")

    @staticmethod
    def seed_progression(historical_apps):
        """Seed valid legacy ownership, an earned badge, and an unpaid clear."""
        from django.db import transaction
        from django.utils import timezone

        def model(name):
            return historical_apps.get_model("pokemon", name)

        player = historical_apps.get_model("objects", "ObjectDB").objects.create(db_key="Migration player")
        trainer = model("Trainer").objects.create(user=player, trainer_number=1)
        badge = model("GymBadge").objects.create(name="Preserved Badge", region="Rehearsal")
        trainer.badges.add(badge)
        leader = model("NPCTrainer").objects.create(name="Migration Alpha Leader")
        profile_model = model("GymLeaderProfile")
        config = {"content_stage": "test"} if any(field.name == "content_stage" for field in profile_model._meta.fields) else {}
        profile = profile_model.objects.create(npc_trainer=leader, badge=badge, league_key="alpha",
                                               gym_key="alpha_gym", badge_key="alpha_badge", **config)
        try:
            victory_model = model("GymVictory")
        except LookupError:
            victory_model = None
        victory = victory_model.objects.create(player=player, metadata={"source_type": "gym_leader",
                                                                         "badge_id": badge.pk}) if victory_model else None
        model("InventoryEntry").objects.create(owner=trainer, item_name="potion", quantity=2)
        storage = model("UserStorage").objects.create(user=player)
        with transaction.atomic():
            pokemon = model("OwnedPokemon").objects.create(
                trainer=trainer, species="Pikachu", level=5, ivs=[0] * 6, evs=[0] * 6,
            )
            model("PokemonPlacement").objects.create(
                pokemon=pokemon, storage=storage, location_type="party", slot=1,
            )
            model("ActivePokemonSlot").objects.create(pokemon=pokemon, storage=storage, slot=1)
        run = model("AdventureSession").objects.create(
            leader=player, template_key="alpha_meadow", current_node="entrance",
            state="completed", completed_at=timezone.now(),
        )
        try:
            participation = model("AdventureParticipation")
        except LookupError:
            participation = None
        if participation is not None:
            participation.objects.create(
                session=run, player=player, route_key="wild", encounter_result="capture",
                completed_at=timezone.now(), reward_item="Potion", reward_amount=1,
            )
        return {"player": player.pk, "trainer": trainer.pk, "badge": badge.pk, "gym": profile.pk,
                "victory": str(victory.pk) if victory else None,
                "pokemon": pokemon.pk, "run": run.pk, "had_participation": participation is not None}

    @staticmethod
    def verify_progression(seed):
        """Exercise recovery after upgrading and retain original inventory/ownership."""
        from django.apps import apps
        from evennia.objects.models import ObjectDB

        from pokemon.adventures.progress import claim_completed_rewards
        from pokemon.models.adventures import AdventureParticipation
        from pokemon.models.core import OwnedPokemon
        from pokemon.models.gym import GymVictory
        from pokemon.models.trainer import GymLeaderProfile, Trainer
        from pokemon.services.placement_audit import audit_placements_v1

        trainer = Trainer.objects.get(pk=seed["trainer"])
        pokemon = OwnedPokemon.objects.get(pk=seed["pokemon"])
        assert pokemon.status == "" and pokemon.sleep_turns is None, "Upgrade introduced a status condition."
        assert trainer.get_item_quantity("Potion") == 2, "Upgrade changed existing inventory."
        assert trainer.badges.filter(pk=seed["badge"]).exists(), "Upgrade lost an earned badge."
        profile = GymLeaderProfile.objects.get(pk=seed["gym"])
        assert profile.content_stage == "test", "Upgrade exposed installed Alpha content to production players."
        assert profile.battle_format == "single" and profile.reward_policy == "legacy"
        if seed["victory"]:
            victory = GymVictory.objects.get(pk=seed["victory"])
            assert victory.claimed_at is None and victory.award_kind == ""
            assert victory.metadata["badge_id"] == seed["badge"], "Upgrade redirected a pending gym award."
        assert not list(audit_placements_v1(apps)), "Upgrade changed valid Pokemon ownership or placement."
        if seed["had_participation"]:
            receipt = AdventureParticipation.objects.get(session_id=seed["run"])
            assert receipt.encounter_result == "capture" and receipt.route_key == "wild"
            assert receipt.reward_claimed_at is None
        player = ObjectDB.objects.get(pk=seed["player"])
        assert "Potion x1" in claim_completed_rewards(player)
        assert claim_completed_rewards(player) == "No unclaimed Adventure rewards."
        assert trainer.get_item_quantity("Potion") == 3, "Recovery duplicated or lost the first-clear reward."


def main():
    """Run each migration scenario in an independent Django process."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=("fresh", *BASELINES))
    args = parser.parse_args()
    if args.scenario is None:
        for scenario in ("fresh", *BASELINES):
            subprocess.run([sys.executable, str(Path(__file__).resolve()), "--scenario", scenario], check=True)
        return
    with IsolatedPostgres():
        RecoveryMigrationRehearsal(args.scenario).run()


if __name__ == "__main__":
    main()
