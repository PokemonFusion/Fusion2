from django import template

from roomeditor.auth import has_builder_access

register = template.Library()


@register.filter
def is_builder(user):
    """Return ``True`` if ``user`` has builder permissions.

    This filter is safe to call with ``None`` (as may happen when rendering
    server error pages where the user context is missing) and will simply
    return ``False`` in that case.
    """
    return has_builder_access(user)


@register.filter(name="class_name")
def class_name(path_or_obj):
    """Return the short class name from a typeclass path or object."""
    if hasattr(path_or_obj, "typeclass_path"):
        path_or_obj = path_or_obj.typeclass_path
    if not isinstance(path_or_obj, str):
        return ""
    return path_or_obj.split(".")[-1]
