import os

import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.conf.settings")
django.setup()


def test_gym_content_models_are_registered_in_admin():
    from django.contrib import admin

    import pokemon.admin as pokemon_admin
    from pokemon.models.trainer import (
        GymBadge,
        GymLeaderProfile,
        NPCPokemonTemplate,
        NPCTrainer,
    )

    assert isinstance(admin.site._registry[GymBadge], pokemon_admin.GymBadgeAdmin)
    assert isinstance(admin.site._registry[GymLeaderProfile], pokemon_admin.GymLeaderProfileAdmin)
    assert isinstance(admin.site._registry[NPCTrainer], pokemon_admin.NPCTrainerAdmin)
    assert isinstance(admin.site._registry[NPCPokemonTemplate], pokemon_admin.NPCPokemonTemplateAdmin)


def test_npc_trainer_admin_exposes_template_inline():
    from django.contrib import admin

    import pokemon.admin as pokemon_admin
    from pokemon.models.trainer import NPCTrainer

    npc_admin = admin.site._registry[NPCTrainer]

    assert pokemon_admin.NPCPokemonTemplateInline in npc_admin.inlines
    assert pokemon_admin.NPCPokemonTemplateInline.model is pokemon_admin.NPCPokemonTemplate
