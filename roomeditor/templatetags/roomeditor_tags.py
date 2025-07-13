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
