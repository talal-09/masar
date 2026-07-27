from django import template


register = template.Library()


@register.simple_tag
def field_value(obj, field_name):
    value = getattr(obj, field_name, "")
    method = getattr(obj, f"get_{field_name}_display", None)
    if callable(method):
        value = method()
    if value is True:
        return "نشط"
    if value is False:
        return "غير نشط"
    if value in (None, ""):
        return "—"
    return value


@register.simple_tag
def field_label(resource, field_name):
    return resource.model._meta.get_field(field_name).verbose_name


@register.filter
def can_change(user, resource):
    return user.is_superuser or user.has_perm(
        f"{resource.model._meta.app_label}.change_{resource.model._meta.model_name}"
    )


@register.filter
def can_delete(user, resource):
    return user.is_superuser or user.has_perm(
        f"{resource.model._meta.app_label}.delete_{resource.model._meta.model_name}"
    )
