"""Utilities for resolving settings-provided locations to actual objects."""

from evennia.objects.models import ObjectDB
from evennia.utils.search import search_object


def resolve_to_obj(val):
    """Resolve various value types to an ``ObjectDB`` instance.

    Parameters
    ----------
    val : Any
        Value specifying an object. This may be a callable, dbref string,
        integer ID, ``ObjectDB`` instance, or name.

    Returns
    -------
    ObjectDB | None
        The resolved object if found, otherwise ``None``.
    """

    if callable(val):
        val = val()
    if isinstance(val, str) and val.startswith("#") and val[1:].isdigit():
        return ObjectDB.objects.filter(id=int(val[1:])).first()
    if isinstance(val, int):
        return ObjectDB.objects.filter(id=val).first()
    if isinstance(val, ObjectDB):
        return val
    if isinstance(val, str):
        objs = search_object(val)
        return objs[0] if objs else None
    return None
