from django import template

register = template.Library()

@register.filter
def is_builder(user):
    if not user.is_authenticated:
        return False
    check = getattr(user, 'check_permstring', None)
    if check:
        return user.is_superuser or check('Builder') or check('Builders')
    return user.is_superuser


@register.filter(name="class_name")
def class_name(path_or_obj):
    """Return the short class name from a typeclass path or object."""
    if hasattr(path_or_obj, "typeclass_path"):
        path_or_obj = path_or_obj.typeclass_path
    if not isinstance(path_or_obj, str):
        return ""
    return path_or_obj.split(".")[-1]
