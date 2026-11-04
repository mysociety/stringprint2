"""
Created on Aug 21, 2016

@author: Alex
"""

from __future__ import annotations

from django import forms
from django.contrib.auth.models import User
from stringprint2.stringprint.models import Organisation, Article


class HoneyPotForm(forms.Form):
    """Reject submissions that fill the hidden phone-number field."""

    phone_number = forms.CharField(label="", required=False, widget=forms.HiddenInput())

    def is_valid(self) -> bool:
        """Return false when a bot has populated the honeypot."""
        valid = super().is_valid()
        return valid and not self.cleaned_data["phone_number"]


class ArticleEditForm(forms.ModelForm):
    title = forms.CharField(label="Document Title", required=True)
    short_title = forms.CharField(
        label="Short Title",
        help_text="One to four word title - used top left as 'the brand'",
        required=True,
    )
    byline = forms.CharField(
        label="Byline",
        help_text="Text displayed below title in document. ",
        required=False,
    )
    description = forms.CharField(
        label="Description",
        help_text="Used as a description in social sharing",
        required=True,
    )
    cite_as = forms.CharField(
        label="Cite As",
        help_text="Used in constructing citations. Recommend switching to Last Name, First name format.",
        required=True,
    )

    class Meta:
        model = Article
        fields = [
            "title",
            "short_title",
            "description",
            "byline",
            "cite_as",
        ]


class OrgAmendForm(forms.ModelForm):
    name = forms.CharField(
        label="Organisation Name",
        help_text="Used in citation construction.",
        required=True,
    )
    twitter = forms.CharField(
        label="Organisation twitter handle",
        help_text="This associated twitter card social sharing\
                            to the correct account",
    )
    ga_code = forms.CharField(
        label="Google Analytics Tracking ID",
        help_text="Format: UA-000000-01 - used to integrate\
                            generated documents into your current tracking.",
        required=False,
    )

    class Meta:
        model = Organisation
        fields = ["name", "twitter", "ga_code"]


class RegisterForm(HoneyPotForm):
    first_name = forms.CharField()
    last_name = forms.CharField()
    org_name = forms.CharField(label="Your organisation's name")
    email = forms.EmailField(label="Email Address")
    password = forms.CharField(widget=forms.PasswordInput)

    def is_valid(self):
        """
        does that email address already exist?
        """
        up = super(RegisterForm, self).is_valid()
        if up:
            email = self.cleaned_data["email"]
            if User.objects.filter(email=email).exists():
                self.add_error(
                    "email", "An account is already using this email address."
                )
                return False
            else:
                return True
        else:
            return False
