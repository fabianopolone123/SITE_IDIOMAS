from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Profile


class RegisterForm(forms.Form):
    username = forms.CharField(label='Username', max_length=150)
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
    full_name = forms.CharField(label='Nome completo', max_length=160)
    whatsapp = forms.CharField(label='Telefone WhatsApp', max_length=30)
    email = forms.EmailField(label='Email')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Esse username ja esta em uso.')
        return username

    def save(self):
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data['username'],
            password=data['password'],
            email=data['email'],
        )
        Profile.objects.create(
            user=user,
            full_name=data['full_name'],
            whatsapp=data['whatsapp'],
        )
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(label='Username')
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
