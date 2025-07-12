import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from pokemon.stats import apply_item_exp_mod, apply_item_ev_mod

class DummyMon:
    def __init__(self, item=None):
        self.item = item
        self.held_item = item


def test_lucky_egg_exp_boost():
    mon = DummyMon("Lucky Egg")
    assert apply_item_exp_mod(mon, 100) == 150


def test_macho_brace_ev_double():
    mon = DummyMon("Macho Brace")
    gains = apply_item_ev_mod(mon, {"atk": 1})
    assert gains["atk"] == 2


def test_power_weight_adds_hp_evs():
    mon = DummyMon("Power Weight")
    gains = apply_item_ev_mod(mon, {"atk": 1})
    assert gains["hp"] == 8
    assert gains["atk"] == 1

