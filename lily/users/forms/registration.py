from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from lily.utils.countries import COUNTRIES
from lily.users.forms.utils import RequiredFirstFormFormset
from lily.utils.forms.widgets import AddonTextInput

from lily.users.models import LilyUser


class ResendActivationMailForm(forms.Form):
    """
    Form that allows a user to retry sending the activation email.
    """
    error_messages = {
        'unknown': _("That email address doesn't have an associated user account. Are you sure you've registered?"),
        'active': _("You cannot request a new activation email for an account that is already active."),
    }

    email = forms.EmailField(
        label=_('Email address'),
        max_length=255,
        widget=AddonTextInput(
            icon_attrs={
                'class': 'fa fa-user',
                'position': 'left',
                'is_button': False
            },
            attrs={
                'class': 'form-control placeholder-no-fix',
                'autocomplete': 'off',
                'placeholder': _('Email address'),
            }
        )
    )

    def clean_email(self):
        """
        Validates that an active user exists with the given email address.
        """
        email = self.cleaned_data['email']
        users_cache = LilyUser.objects.filter(email__iexact=email)
        if not len(users_cache):
            raise ValidationError(code='invalid', message=self.error_messages['unknown'])
        else:
            for user in users_cache:
                if user.is_active:
                    raise ValidationError(code='invalid', message=self.error_messages['active'])
        return email


class UserRegistrationForm(forms.Form):
    """
    This form allows new user registration.
    """
    email = forms.EmailField(label=_('Email'), max_length=255)
    password = forms.CharField(
        label=_('Password'),
        min_length=6,
        widget=forms.PasswordInput(),
        help_text='Password should be at least 6 characters long.',
    )

    first_name = forms.CharField(label=_('First name'), max_length=255)
    last_name = forms.CharField(label=_('Last name'), max_length=255)

    def clean_email(self):
        if LilyUser.objects.filter(email__iexact=self.cleaned_data['email']).exists():
            raise ValidationError(code='invalid', message=_('Email address already in use.'))
        else:
            return self.cleaned_data['email']


class TenantRegistrationForm(UserRegistrationForm):
    """
    This form allows new tenant registration.
    """
    tenant_name = forms.CharField(label=_('Company name'), max_length=255)
    country = forms.ChoiceField(COUNTRIES)

    def __init__(self, *args, **kwargs):
        super(TenantRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = _('Enter your first name')
        self.fields['last_name'].widget.attrs['placeholder'] = _('Enter your last name')
        self.fields['tenant_name'].widget.attrs['placeholder'] = _('Enter the name of your company')
        self.fields['email'].widget.attrs['placeholder'] = _('youremail@example.com')


class AcceptInvitationForm(UserRegistrationForm):
    """
    Form for accepting invitations.
    """
    email = forms.EmailField(
        label=_('Email'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'mws-register-email disabled',
            'readonly': 'readonly',
        })
    )

    def clean_email(self):
        if self.cleaned_data['email'] != self.initial['email']:
            raise ValidationError(code='invalid', message=_('You can\'t change the email address of the invitation.'))
        else:
            return self.cleaned_data['email']


class SendInvitationForm(forms.Form):
    """
    This is the invitation form, it is used to invite new users to join an account.
    """
    first_name = forms.CharField(
        label=_('First name'),
        max_length=255,
        widget=forms.TextInput(attrs={
            'placeholder': _('First name')
        })
    )
    email = forms.EmailField(
        label=_('Email'),
        max_length=255,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': _('Email address')
        })
    )

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            LilyUser.objects.get(email__iexact=email)
        except LilyUser.DoesNotExist:
            return email
        else:
            raise ValidationError(code='invalid', message=_('This email address is already linked to a user.'))


# ------------------------------------------------------------------------------------------------
# Formsets
# ------------------------------------------------------------------------------------------------
class InvitationFormset(RequiredFirstFormFormset):
    """
    This formset is sending invitations to users based on email addresses.
    """
    def clean(self):
        """Checks that no two email addresses are the same."""
        super(InvitationFormset, self).clean()

        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own
            return
        emails = []
        for i in range(0, self.total_form_count()):
            form = self.forms[i]
            email = form.cleaned_data['email']
            if email and email in emails:
                raise ValidationError(
                    code='invalid',
                    message=_('You can\'t invite someone more than once (email addresses must be unique).')
                )
            emails.append(email)