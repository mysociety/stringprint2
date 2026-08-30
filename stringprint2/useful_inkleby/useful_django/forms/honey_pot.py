
from django import forms


class HoneyPotForm(forms.Form):
    """
    Form that adds a fake phone number field to try and trick bots
    """
    phone_number = forms.CharField(label="",
                                   required=False,
                                   widget=forms.HiddenInput())

    def is_valid(self):
        """
        checks to see no bot has put anything in the phone number field
        """

        valid = super(HoneyPotForm, self).is_valid()

        if self.cleaned_data['phone_number']:
            return False
        else:
            return valid
