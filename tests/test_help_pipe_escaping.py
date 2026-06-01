import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GROUP_WITH_PIPE_RE = re.compile(r"(?:\[[^\]\n]*\|[^\]\n]*\]|<[^>\n]*\|[^>\n]*>)")
SINGLE_PIPE_RE = re.compile(r"(?<!\|)\|(?!\|)")


def _string_lines(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            for lineno, line in enumerate(node.value.splitlines(), start=getattr(node, "lineno", 0)):
                yield lineno, line.strip()


def test_grouped_help_option_pipes_are_escaped():
    """Literal pipes in help options must be doubled for Evennia ANSI output."""

    offenders = []
    for base in (ROOT / "commands", ROOT / "world"):
        for path in base.rglob("*.py"):
            for lineno, line in _string_lines(path):
                for group in GROUP_WITH_PIPE_RE.findall(line):
                    if SINGLE_PIPE_RE.search(group):
                        offenders.append(f"{path.relative_to(ROOT)}:{lineno}: {line}")

    assert offenders == []
