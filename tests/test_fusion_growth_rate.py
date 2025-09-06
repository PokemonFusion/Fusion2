
import types

from pokemon.models.stats import exp_for_level, level_for_exp, add_experience
from utils.xp_utils import get_next_level_xp
from utils.fusion import record_fusion


def test_exp_level_conversion_for_slow_rate():
    for level in [1, 5, 10]:
        exp = exp_for_level(level, 'slow')
        assert level_for_exp(exp, 'slow') == level
        if level > 1:
            assert level_for_exp(exp - 1, 'slow') == level - 1


def test_add_experience_uses_growth_rate():
    mon = types.SimpleNamespace(experience=0, level=1, growth_rate='slow')
    add_experience(mon, exp_for_level(10, 'slow') - 1)
    assert mon.level == 9
    add_experience(mon, 1)
    assert mon.level == 10


def test_get_next_level_xp_respects_growth_rate():
    mon = types.SimpleNamespace(total_exp=125, growth_rate='slow')
    next_xp = get_next_level_xp(mon)
    assert next_xp == exp_for_level(5, 'slow')


def test_record_fusion_adopts_growth_rate():
    source = types.SimpleNamespace(growth_rate='slow')
    result = types.SimpleNamespace()
    trainer = types.SimpleNamespace()
    record_fusion(result, trainer, source, permanent=True)
    assert getattr(result, 'growth_rate', '') == 'slow'
