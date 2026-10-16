"""Metadata for supported game items omitted from the competitive item dex."""

from dataclasses import dataclass

from pokemon.names import normalize_name


@dataclass(frozen=True)
class GameplayItem:
    """Share a complete display name and description across item interfaces."""

    name: str
    desc: str

    @property
    def raw(self) -> dict[str, str]:
        """Match the metadata interface used by dex-backed item displays."""
        return {"name": self.name, "desc": self.desc}


GAMEPLAY_ITEMS = {
    "everstone": GameplayItem("Everstone", "Prevents the holder from evolving."),
    "blackaugurite": GameplayItem("Black Augurite", "Evolves Scyther into Kleavor."),
}


def get_gameplay_item(name: object) -> GameplayItem | None:
    """Resolve complete normalized names; prefixes remain invalid."""
    return GAMEPLAY_ITEMS.get(normalize_name(name))
