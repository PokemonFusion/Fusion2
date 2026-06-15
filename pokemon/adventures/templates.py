"""Code-defined Adventure templates for the MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class AdventureObjective:
    """Template description for one objective."""

    key: str
    type: str
    description: str
    target_node: str = ""
    required: bool = True


@dataclass(frozen=True)
class AdventureNode:
    """A virtual location inside an Adventure."""

    key: str
    name: str
    description: str
    exits: Mapping[str, str] = field(default_factory=dict)
    search_text: str = ""
    search_objective: str = ""
    coordinates: tuple[int, int] | None = None


@dataclass(frozen=True)
class AdventureTemplate:
    """Reusable Adventure definition."""

    key: str
    name: str
    description: str
    category: str
    region: str
    biome: str
    start_node: str
    nodes: Mapping[str, AdventureNode]
    objectives: tuple[AdventureObjective, ...]
    max_party_size: int = 1
    recommended_level: str = "Any"
    status: str = "active"


ALPHA_MEADOW = AdventureTemplate(
    key="alpha_meadow",
    name="Alpha Meadow Survey",
    description=(
        "A small non-combat survey route for testing virtual movement, "
        "objectives, and clean adventure exits."
    ),
    category="hunt/tutorial",
    region="Alpha",
    biome="meadow",
    start_node="entrance",
    nodes={
        "entrance": AdventureNode(
            key="entrance",
            name="Meadow Entrance",
            description=(
                "A short grass trail opens into a quiet meadow. The Adventure "
                "Hall exit shimmers behind you."
            ),
            exits={"north": "tall_grass"},
            coordinates=(0, 0),
        ),
        "tall_grass": AdventureNode(
            key="tall_grass",
            name="Tall Grass Path",
            description=(
                "Tall grass bends in the breeze. Something small rustles out "
                "of sight, but this survey is not using battle encounters yet."
            ),
            exits={"south": "entrance", "east": "small_pond", "north": "old_tree"},
            coordinates=(0, 1),
        ),
        "small_pond": AdventureNode(
            key="small_pond",
            name="Small Pond",
            description=(
                "Clear water gathers beside smooth stones. Ripple marks show "
                "where Pokemon might gather once encounters are enabled."
            ),
            exits={"west": "tall_grass"},
            coordinates=(1, 1),
        ),
        "old_tree": AdventureNode(
            key="old_tree",
            name="Old Tree",
            description=(
                "An old tree leans over the meadow, its roots circling a patch "
                "of disturbed soil."
            ),
            exits={"south": "tall_grass"},
            search_text="You find fresh tracks and mark the Old Tree survey point.",
            search_objective="search_old_tree",
            coordinates=(0, 2),
        ),
    },
    objectives=(
        AdventureObjective(
            key="reach_old_tree",
            type="reach",
            description="Reach the Old Tree.",
            target_node="old_tree",
        ),
        AdventureObjective(
            key="search_old_tree",
            type="search",
            description="Search the Old Tree.",
            target_node="old_tree",
        ),
        AdventureObjective(
            key="return_entrance",
            type="return",
            description="Return to the Meadow Entrance.",
            target_node="entrance",
        ),
    ),
)


_TEMPLATES = {ALPHA_MEADOW.key: ALPHA_MEADOW}


def list_templates() -> list[AdventureTemplate]:
    """Return all player-visible Adventure templates."""

    return sorted(_TEMPLATES.values(), key=lambda template: template.name)


def get_template(key_or_name: str) -> AdventureTemplate | None:
    """Resolve an Adventure template by key or case-insensitive name."""

    query = (key_or_name or "").strip().lower()
    if not query:
        return None
    if query in _TEMPLATES:
        return _TEMPLATES[query]
    for template in _TEMPLATES.values():
        if query == template.name.lower():
            return template
    return None


def validate_template(template: AdventureTemplate) -> list[str]:
    """Return validation errors for ``template``."""

    errors: list[str] = []
    if not template.key:
        errors.append("Template key is required.")
    if template.start_node not in template.nodes:
        errors.append(f"Start node '{template.start_node}' is missing.")
    for node in template.nodes.values():
        if not node.key:
            errors.append("Node key is required.")
        for direction, target in node.exits.items():
            if target not in template.nodes:
                errors.append(f"Node '{node.key}' exit '{direction}' points to missing node '{target}'.")
    for objective in template.objectives:
        if not objective.key:
            errors.append("Objective key is required.")
        if objective.target_node and objective.target_node not in template.nodes:
            errors.append(
                f"Objective '{objective.key}' target node '{objective.target_node}' is missing."
            )
    return errors


def initial_objective_progress(template: AdventureTemplate) -> dict[str, int]:
    """Return the default progress map for a new session."""

    return {objective.key: 0 for objective in template.objectives}
