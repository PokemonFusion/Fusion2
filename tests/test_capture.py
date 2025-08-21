import os
import random
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Prepare package (reuse existing stub if present)
import importlib.util
import types

pkg_battle = sys.modules.get("pokemon.battle")
if pkg_battle is None:
	pkg_battle = types.ModuleType("pokemon.battle")
	pkg_battle.__path__ = []
	sys.modules["pokemon.battle"] = pkg_battle

# Load capture module and attach to package
capture_path = os.path.join(ROOT, "pokemon", "battle", "capture.py")
spec = importlib.util.spec_from_file_location("pokemon.battle.capture", capture_path)
capture_mod = importlib.util.module_from_spec(spec)
sys.modules["pokemon.battle.capture"] = capture_mod
spec.loader.exec_module(capture_mod)
pkg_battle.capture = capture_mod
attempt_capture = capture_mod.attempt_capture


def test_auto_capture_when_a_high():
	rng = random.Random(0)
	assert attempt_capture(100, 1, 255, rng=rng)


def test_deterministic_capture():
	rng = random.Random(0)
	res1 = attempt_capture(100, 50, 45, rng=rng)
	assert res1 is False
	rng.seed(1)
	res2 = attempt_capture(100, 50, 45, rng=rng)
	assert res2 is True
