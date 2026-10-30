import importlib

mod = importlib.import_module("utils.xp_utils")
get_display_xp = mod.get_display_xp
get_next_level_xp = mod.get_next_level_xp


class DummyMon:
        def __init__(self, **attrs):
                for k, v in attrs.items():
                        setattr(self, k, v)


def test_get_display_xp_attribute():
	mon = DummyMon(xp=250)
	assert get_display_xp(mon) == 250


def test_get_display_xp_from_total_exp():
	mon = DummyMon(total_exp=300)
	assert get_display_xp(mon) == 300


def test_get_display_xp_missing():
        mon = DummyMon()
        assert get_display_xp(mon) == 0


def test_get_display_xp_from_db():
        mon = DummyMon()
        mon.db = DummyMon(total_exp=450)
        assert get_display_xp(mon) == 450


def test_get_next_level_xp():
	mon = DummyMon(total_exp=125)
	next_xp = get_next_level_xp(mon)
	# Level for 125 XP should be 5 -> next level 6 -> exp_for_level(6) = 216
	assert next_xp == 216
