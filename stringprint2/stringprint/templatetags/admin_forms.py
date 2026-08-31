"""Template helpers for rendering Django forms with Bootstrap 5."""

from __future__ import annotations

from django import template
from django.forms import BoundField
from django.forms.widgets import CheckboxInput, Select
from django.utils.safestring import SafeString, mark_safe

register = template.Library()


@register.filter
def bootstrap_widget(field: BoundField) -> SafeString:
    """Render a bound field with the appropriate Bootstrap 5 widget class."""
    widget = field.field.widget
    if isinstance(widget, CheckboxInput):
        css_class = "form-check-input"
    elif isinstance(widget, Select):
        css_class = "form-select"
    else:
        css_class = "form-control"
    existing_class = widget.attrs.get("class", "")
    classes = " ".join(value for value in (existing_class, css_class) if value)
    if field.errors:
        classes = f"{classes} is-invalid"
    return mark_safe(field.as_widget(attrs={"class": classes}))
