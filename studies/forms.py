from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User

from .models import Profile
from .models import VanRegistration


class RegisterForm(forms.Form):
    username = forms.CharField(label='Username', max_length=150)
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)
    full_name = forms.CharField(label='Nome completo', max_length=160)
    whatsapp = forms.CharField(label='Telefone WhatsApp', max_length=30)
    email = forms.EmailField(label='Email')

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('Esse username já está em uso.')
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


class VanRegistrationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['minor_cpf', 'event_start_date', 'event_end_date', 'city', 'signature_date']:
            self.fields[field_name].required = True

    class Meta:
        model = VanRegistration
        fields = [
            'responsible_name',
            'responsible_cpf',
            'responsible_phone',
            'responsible_phone_alt',
            'minor_name',
            'minor_cpf',
            'event_name',
            'event_start_date',
            'event_end_date',
            'health_info',
            'city',
            'signature_date',
        ]
        widgets = {
            'event_start_date': forms.DateInput(attrs={'type': 'date'}),
            'event_end_date': forms.DateInput(attrs={'type': 'date'}),
            'signature_date': forms.DateInput(attrs={'type': 'date'}),
            'health_info': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'responsible_name': 'Nome completo do responsável legal',
            'responsible_cpf': 'CPF do responsável',
            'responsible_phone': 'Telefone do responsável',
            'responsible_phone_alt': 'Segundo telefone do responsável',
            'minor_name': 'Nome completo do adolescente',
            'minor_cpf': 'CPF do adolescente',
            'event_name': 'Nome do evento',
            'event_start_date': 'Data inicial do evento',
            'event_end_date': 'Data final do evento',
            'health_info': 'Informações importantes de saúde',
            'city': 'Cidade',
            'signature_date': 'Data do termo',
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.transport_by = 'van'
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class VanConsultForm(forms.Form):
    responsible_cpf = forms.CharField(label='CPF do responsável', max_length=20)
    minor_cpf = forms.CharField(label='CPF do adolescente', max_length=20)


class VanSignedTermForm(forms.ModelForm):
    class Meta:
        model = VanRegistration
        fields = ['signed_term']
        labels = {'signed_term': 'Enviar termo assinado em PDF'}

    def clean_signed_term(self):
        file = self.cleaned_data.get('signed_term')
        if not file:
            raise forms.ValidationError('Envie o termo assinado.')
        if not file.name.lower().endswith('.pdf'):
            raise forms.ValidationError('Envie um arquivo PDF.')
        if file.size > 10 * 1024 * 1024:
            raise forms.ValidationError('O arquivo deve ter no máximo 10 MB.')
        return file


class VanAdminLoginForm(forms.Form):
    password = forms.CharField(label='Senha', widget=forms.PasswordInput)

    def clean_password(self):
        password = self.cleaned_data['password']
        if password != '1580':
            raise forms.ValidationError('Senha inválida.')
        return password
