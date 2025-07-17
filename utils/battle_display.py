from __future__ import annotations


def render_move_gui(moves: dict) -> str:
    """Render the four-move GUI block as a string.

    Args:
        moves: mapping of slot letters to move info dicts with keys ``name``,
            ``type``, ``category``, ``pp`` (tuple), ``power`` and ``accuracy``.

    Returns:
        str: formatted GUI string.
    """

    def render_box(label: str, move: dict) -> str:
        name = move.get("name", "???")
        mtype = move.get("type") or "???"
        cat = move.get("category") or "???"
        pp_cur, pp_max = move.get("pp", (0, 0))
        pp_cur = pp_cur if pp_cur is not None else 0
        pp_max = pp_max if pp_max is not None else 0
        power = move.get("power", 0)
        acc = move.get("accuracy", 0)
        return (
            f"/-----------------{label}------------------\\"
            f"\n|  {name:<32}|"
            f"\n|  {mtype:<15}{cat:<17}|"
            f"\n|  PP:  {pp_cur}/{pp_max:<24}|"
            f"\n|  Power: {power:<6}   Accuracy: {acc:<6}|"
            f"\n\\------------------------------------/"
        )

    top = render_box("A", moves.get("A", {})) + " " + render_box("B", moves.get("B", {}))
    bot = render_box("C", moves.get("C", {})) + " " + render_box("D", moves.get("D", {}))
    return f"{top}\n{bot}\n|r<Battle>|n Pick an attack, use '|r.abort|n' to cancel:"
