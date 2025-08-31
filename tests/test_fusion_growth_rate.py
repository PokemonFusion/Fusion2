import types

from pokemon.models.stats import exp_for_level, level_for_exp, add_experience
from utils.xp_utils import get_next_level_xp
from utils.fusion import record_fusion


def test_exp_level_conversion_fusion():
    for level in [1, 5, 10]:
        exp = exp_for_level(level, "fusion")
        assert level_for_exp(exp, "fusion") == level
        if level > 1:
            assert level_for_exp(exp - 1, "fusion") == level - 1


def test_add_experience_updates_level_fusion():
    mon = types.SimpleNamespace(experience=0, level=1, growth_rate="fusion")
    add_experience(mon, exp_for_level(10, "fusion") - 1)
    assert mon.level == 9
    add_experience(mon, 1)
    assert mon.level == 10


def test_get_next_level_xp_fusion():
    mon = types.SimpleNamespace(total_exp=125, growth_rate="fusion")
    next_xp = get_next_level_xp(mon)
    assert next_xp == exp_for_level(4, "fusion")


def test_record_fusion_sets_growth_rate():
    mon = types.SimpleNamespace()
    trainer = types.SimpleNamespace()
    record_fusion(mon, trainer, mon, permanent=True)
    assert getattr(mon, "growth_rate", "") == "fusion"
