import importlib
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Load the berry_system module
berry_mod = importlib.import_module('pokemon.helpers.berry_system')
BerryPlant = berry_mod.BerryPlant


def test_growth_progression():
    plant = BerryPlant('oran', growth_time=10)
    plant.progress(10)
    assert plant.stage == 1
    plant.progress(20)
    assert plant.stage == 3


def test_harvest_yield():
    plant = BerryPlant('oran', growth_time=1)
    for _ in range(3):
        plant.water()
    plant.progress(5)
    assert plant.is_ready()
    amount = plant.harvest()
    assert amount == 4
    assert plant.stage == 0
