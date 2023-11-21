"""
Created on Aug 21, 2016

@author: Alex
"""
from django import forms
from useful_inkleby.useful_django.forms import HoneyPotForm
from django.contrib.auth.models import User
from stringprint.models import Organisation, Article, HeaderImage
from django.core.exceptions import ValidationError
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe


class AdminImageWidget(AdminFileWidget):
    def render(self, name, value, attrs=None):
        output = []
        if value and getattr(value, "url", None):
            image_url = value.url
            file_name = str(value)
            output.append(
                ' <a href="%s" target="_blank"><img src="%s" alt="%s" width=300 /></a>'
                % (image_url, image_url, file_name)
            )
        output.append(super(AdminFileWidget, self).render(name, value, attrs))

        output = ["<td>{0}</td>".format(x) for x in output if x]
        output = "".join(output)
        final = "<table><tr>" + output + "</tr></table>"

        # print final
        return mark_safe(final)


class PageHeaderImageForm(forms.ModelForm):
    image = forms.ImageField(label="Image", widget=AdminImageWidget, required=False)
    image_vertical = forms.ImageField(
        label="Responsive Image",
        help_text="If present, used for mobile screens.\
                                      You might want a more vertical image",
        widget=AdminImageWidget,
        required=False,
    )
    size = forms.IntegerField(
        max_value=12,
        min_value=0,
        help_text="How many 12ths of the screen should the\
                              image take up? 6 is half, etc. Use 0 for full width.",
    )
    image_alt = forms.CharField(
        label="Alt Text",
        required=False,
        help_text="Description of header for accessibility",
    )

    def save(self, article, commit=True, files=None):
        prior = self.instance.image.name
        prior_h = self.instance.image_vertical.name

        ins = super(PageHeaderImageForm, self).save(commit=False)

        if commit:
            if (
                hasattr(ins, "prior") == False
                or ins.prior != prior
                or ins.prior_h != prior_h
            ):
                ins.queue_tiny = True
                ins.title_image = True
                ins.article = article
                if "image" in files:
                    ins.image.save(files["image"].name, files["image"])
                    print(files["image"].name)
                if "image_vertical" in files:
                    ins.image_vertical.save(
                        files["image_vertical"].name, files["image_vertical"]
                    )
                ins.save()
                ins.trigger_create_responsive()

    class Meta:
        model = HeaderImage
        fields = ["image", "image_vertical", "image_alt", "size"]


class ArticlePublishForm(forms.Form):
    publish_url = forms.CharField(
        label="Final URL",
        help_text="Where will this document be visible on the web? (used for social sharing).",
        required=True,
    )
    publish_date = forms.DateField(
        label="Publish Date",
        widget=forms.DateInput(attrs={"class": "datepicker"}),
        help_text="When will this document be first published?",
        required=True,
    )

    def __init__(self, *args, **kwargs):
        setting_url = kwargs.pop("setting_url", "http://www.test.com")
        super(ArticlePublishForm, self).__init__(*args, **kwargs)
        pu = self.fields["publish_url"]
        pu.help_text += "e.g. {0}".format(setting_url)
        pu.widget = forms.TextInput(attrs={"placeholder": setting_url})


class KindleEditForm(forms.ModelForm):
    book_cover = forms.ImageField(
        label="Kindle Book Cover",
        required=True,
        widget=AdminImageWidget,
    )

    class Meta:
        model = Article
        fields = ["book_cover"]


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


def validate_file_extension(value):
    if not value.name.endswith(".pdf"):
        raise ValidationError("Error message")


class ReuploadWordForm(HoneyPotForm):
    file = forms.FileField(
        label="Upload a Word file (optional)",
        required=False,
        validators=[validate_file_extension],
    )


class NewDocumentForm(HoneyPotForm):
    title = forms.CharField(
        label="Document Title", help_text="Don't worry, this can be changed later."
    )
    file = forms.FileField(
        label="Upload a Word file (optional)",
        required=False,
        validators=[validate_file_extension],
    )


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
