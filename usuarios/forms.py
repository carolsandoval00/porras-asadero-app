import re

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

from .models import Usuario


# ─── Validadores reutilizables de nombres ──────────────────────
def _validar_nombre(value, campo='nombre', max_length=100):
    """Valida que el nombre sea real: solo letras, con longitud razonable, mínimo 2
    caracteres, que contenga al menos una vocal y que no repita el mismo carácter."""
    if not value:
        raise ValidationError(f'El {campo} es obligatorio.')
    texto = str(value).strip()

    if len(texto) < 2:
        raise ValidationError(f'El {campo} debe tener al menos 2 caracteres.')
    if len(texto) > max_length:
        raise ValidationError(f'El {campo} no puede superar {max_length} caracteres.')

    if not re.fullmatch(r'[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ\s]+', texto):
        raise ValidationError(f'El {campo} solo puede contener letras y espacios.')

    # Rechazar si todos los caracteres son iguales (ej: "hhhhhhhh")
    if len(set(texto.replace(' ', ''))) < 2:
        raise ValidationError(f'El {campo} no puede ser un solo carácter repetido.')

    # Debe tener al menos una vocal
    if not re.search(r'[aeiouáéíóúüAEIOUÁÉÍÓÚÜ]', texto):
        raise ValidationError(f'El {campo} debe incluir al menos una vocal.')

    return texto


def _validar_palabras(value, campo='nombre', min_palabras=2):
    """Valida que el nombre completo tenga al menos N palabras."""
    texto = _validar_nombre(value, campo=campo, max_length=200)
    palabras = texto.split()
    if len(palabras) < min_palabras:
        raise ValidationError(f'El {campo} debe incluir nombre y apellido (mínimo {min_palabras} palabras).')
    return texto


class CustomPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Ingresa tu correo'
        })

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError('El correo electrónico es obligatorio.')
        return email


class PersonalForm(forms.ModelForm):
    """Formulario para crear/editar personal administrativo."""

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'username', 'email', 'rol']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_first_name(self):
        return _validar_nombre(self.cleaned_data.get('first_name', ''), campo='nombre')

    def clean_last_name(self):
        return _validar_nombre(self.cleaned_data.get('last_name', ''), campo='apellido')

    def clean_username(self):
        usuario = self.cleaned_data.get('username', '').strip()
        if not usuario:
            raise ValidationError('El nombre de usuario es obligatorio.')
        if not re.fullmatch(r'[a-zA-Z0-9_.]+', usuario):
            raise ValidationError('El usuario solo puede contener letras, números, punto y guion bajo.')
        if len(usuario) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        if Usuario.objects.filter(username=usuario).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Ese nombre de usuario ya está en uso.')
        return usuario

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError('El correo electrónico es obligatorio.')
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Ese correo electrónico ya está registrado.')
        return email

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        if not rol:
            raise ValidationError('Debes seleccionar un rol.')
        return rol


class RegistroForm(forms.ModelForm):
    """Formulario de registro público de usuarios."""

    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    password2 = forms.CharField(widget=forms.PasswordInput, min_length=6)

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'password2']

    def clean_first_name(self):
        return _validar_nombre(self.cleaned_data.get('first_name', ''), campo='nombre')

    def clean_last_name(self):
        return _validar_nombre(self.cleaned_data.get('last_name', ''), campo='apellido')

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if not email:
            raise ValidationError('El correo electrónico es obligatorio.')
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ese correo electrónico ya está registrado.')
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if not username:
            raise ValidationError('El nombre de usuario es obligatorio.')
        if len(username) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError('Ese nombre de usuario ya está en uso.')
        return username

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 6:
            raise ValidationError('La contraseña debe tener al menos 6 caracteres.')
        if not re.search(r'[A-Z]', password):
            raise ValidationError('La contraseña debe incluir al menos una mayúscula.')
        if not re.search(r'[a-z]', password):
            raise ValidationError('La contraseña debe incluir al menos una minúscula.')
        if not re.search(r'[0-9]', password):
            raise ValidationError('La contraseña debe incluir al menos un número.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data
