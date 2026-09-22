"""Regression tests for Bootstrap 5 management form rendering."""

from __future__ import annotations

from django import forms
from django.template.loader import render_to_string


class ExampleManagementForm(forms.Form):
    """Exercise the widget categories used by management forms."""

    title = forms.CharField(help_text="Shown publicly")
    format = forms.ChoiceField(choices=(("web", "Web"),))
    refresh = forms.BooleanField(required=False)


def test_management_form_uses_bootstrap_5_widget_classes() -> None:
    """Local form rendering applies Bootstrap 5 classes without bootstrapform."""
    rendered = render_to_string(
        "frontend/bootstrap_form.html",
        {"form": ExampleManagementForm()},
    )

    assert 'class="form-control"' in rendered
    assert 'class="form-select"' in rendered
    assert 'class="form-check-input"' in rendered
    assert 'class="form-label"' in rendered
    assert "Shown publicly" in rendered


def test_management_form_displays_validation_errors() -> None:
    """Invalid fields expose both Bootstrap state and readable error text."""
    form = ExampleManagementForm(data={"title": "", "format": "missing"})
    assert not form.is_valid()

    rendered = render_to_string("frontend/bootstrap_form.html", {"form": form})

    assert "is-invalid" in rendered
    assert "This field is required." in rendered
    assert "Select a valid choice" in rendered
