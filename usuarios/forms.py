import re

from django import forms
from django.contrib.auth.forms import PasswordResetForm
from django.core.exceptions import ValidationError

from .models import Usuario
from .validators import (
    validar_nombre,
    validar_documento,
    validar_telefono,
    validar_correo,
    validar_password,
)


# ─── Compatibilidad: otros módulos importan estos nombres ──────
def _validar_nombre(value, campo='nombre', max_length=60):
    """Alias de validators.validar_nombre (se conserva por compatibilidad con views.py)."""
    return validar_nombre(value, campo=campo, max_length=max_length)


def _validar_palabras(value, campo='nombre', min_palabras=2):
    """Valida que el nombre completo tenga al menos N palabras."""
    texto = validar_nombre(value, campo=campo, max_length=120)
    if len(texto.split()) < min_palabras:
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
    """
    Formulario para crear personal desde "Nuevo usuario" (lista de personal).

    Valida: nombres/apellidos reales, documento con formato Colombia,
    correo real y contraseña de 6 a 8 caracteres con mayúscula, minúscula,
    número y símbolo.
    """

    # Campos que no son del modelo o que se validan a mano
    tipo_documento = forms.CharField(required=False)
    documento = forms.CharField(required=False)
    telefono = forms.CharField(required=False)
    password = forms.CharField(required=False)
    password2 = forms.CharField(required=False)

    # Al crear, la contraseña es obligatoria. Al editar se deja en False.
    exigir_password = True

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Mensajes en el mismo tono del aviso "Atención"
        self.fields['email'].error_messages.update({
            'required': 'Debes escribir el correo electrónico.',
            'invalid': 'Escribe un correo real (ej: nombre@gmail.com).',
        })
        self.fields['rol'].error_messages.update({
            'required': 'Debes elegir un rol para el usuario.',
            'invalid_choice': 'Debes elegir un rol para el usuario.',
        })
        if 'username' in self.fields:
            self.fields['username'].error_messages['required'] = 'Debes escribir el nombre de usuario.'

    def _pk(self):
        return self.instance.pk if self.instance else None

    # ── 1. Nombres y apellidos ────────────────────────────────
    def clean_first_name(self):
        return validar_nombre(self.cleaned_data.get('first_name', ''), campo='nombre')

    def clean_last_name(self):
        return validar_nombre(self.cleaned_data.get('last_name', ''), campo='apellido')

    # ── Usuario ───────────────────────────────────────────────
    def clean_username(self):
        usuario = (self.cleaned_data.get('username') or '').strip()
        if not usuario:
            raise ValidationError('Debes escribir el nombre de usuario.')
        if len(usuario) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        if not re.fullmatch(r'[a-zA-Z0-9_.]+', usuario):
            raise ValidationError('El usuario solo puede contener letras, números, punto y guion bajo.')
        if Usuario.objects.filter(username=usuario).exclude(pk=self._pk()).exists():
            raise ValidationError('Ese nombre de usuario ya está en uso.')
        return usuario

    # ── 3. Correo ─────────────────────────────────────────────
    def clean_email(self):
        email = validar_correo(self.cleaned_data.get('email', ''))
        if Usuario.objects.filter(email__iexact=email).exclude(pk=self._pk()).exists():
            raise ValidationError('Ese correo electrónico ya está registrado.')
        return email

    def clean_rol(self):
        rol = self.cleaned_data.get('rol')
        if not rol:
            raise ValidationError('Debes seleccionar un rol.')
        return rol

    def _clean_telefono(self, cleaned):
        """Teléfono opcional: si se escribe, 10 dígitos y empieza por 3."""
        try:
            cleaned['telefono'] = validar_telefono(self.data.get('telefono'))
        except ValidationError as e:
            self.add_error('telefono', e)

    # ── 2. Documento y 4. Contraseña (dependen de otros campos) ──
    def clean(self):
        cleaned = super().clean()

        try:
            doc = validar_documento(self.data.get('tipo_documento'), self.data.get('documento'))
            if doc and Usuario.objects.filter(documento=doc).exclude(pk=self._pk()).exists():
                raise ValidationError('Ese número de documento ya está registrado.')
            cleaned['documento'] = doc  # None si no se escribió
        except ValidationError as e:
            self.add_error('documento', e)

        self._clean_telefono(cleaned)

        password = self.data.get('password') or ''
        password2 = self.data.get('password2') or ''
        if self.exigir_password or password:
            try:
                validar_password(password, usuario=cleaned.get('username', ''))
            except ValidationError as e:
                self.add_error('password', e)
            else:
                if password != password2:
                    self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned


class PersonalEditarForm(PersonalForm):
    """
    Edición de personal. No toca el usuario, la contraseña es opcional y el
    nombre, apellido, correo, documento y teléfono solo se revalidan si el administrador los cambió
    (así no se bloquean cuentas antiguas).
    """

    exigir_password = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        del self.fields['username']

    def clean_first_name(self):
        valor = (self.cleaned_data.get('first_name') or '').strip()
        if self.instance.pk and valor and valor == (self.instance.first_name or ''):
            return valor                       # sin cambios: no se revalida (cuentas antiguas)
        return super().clean_first_name()

    def clean_last_name(self):
        valor = (self.cleaned_data.get('last_name') or '').strip()
        if self.instance.pk and valor and valor == (self.instance.last_name or ''):
            return valor
        return super().clean_last_name()

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if self.instance.pk and email == (self.instance.email or '').lower():
            return email
        return super().clean_email()

    def clean(self):
        cleaned = forms.ModelForm.clean(self)

        tipo = self.data.get('tipo_documento')
        numero = self.data.get('documento')
        sin_cambios = (
            self.instance.pk
            and (numero or '') == (self.instance.documento or '')
            and (self.instance.documento or '') != ''
        )
        if sin_cambios:
            cleaned['documento'] = numero
        else:
            try:
                doc = validar_documento(tipo, numero)
                if doc and Usuario.objects.filter(documento=doc).exclude(pk=self._pk()).exists():
                    raise ValidationError('Ese número de documento ya está registrado.')
                cleaned['documento'] = doc
            except ValidationError as e:
                self.add_error('documento', e)

        tel = (self.data.get('telefono') or '').strip()
        if self.instance.pk and tel and tel == (self.instance.telefono or ''):
            cleaned['telefono'] = tel          # sin cambios: no se revalida (cuentas antiguas)
        else:
            self._clean_telefono(cleaned)

        password = self.data.get('password') or ''
        password2 = self.data.get('password2') or ''
        if password:
            try:
                validar_password(password, usuario=self.instance.username)
            except ValidationError as e:
                self.add_error('password', e)
            else:
                if password != password2:
                    self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned


class RegistroForm(forms.ModelForm):
    """Formulario de registro público de usuarios."""

    # Sin min_length/max_length de Django: las reglas y mensajes están en clean_password
    password = forms.CharField(widget=forms.PasswordInput(render_value=False))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False))

    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'email', 'username', 'password', 'password2']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].error_messages.update({
            'required': 'Debes escribir el correo electrónico.',
            'invalid': 'Escribe un correo real (ej: nombre@gmail.com).',
        })
        self.fields['username'].error_messages['required'] = 'Debes escribir el nombre de usuario.'
        self.fields['password'].error_messages['required'] = 'Debes escribir la contraseña.'
        self.fields['password2'].error_messages['required'] = 'Debes confirmar la contraseña.'

    def clean_first_name(self):
        return validar_nombre(self.cleaned_data.get('first_name', ''), campo='nombre')

    def clean_last_name(self):
        return validar_nombre(self.cleaned_data.get('last_name', ''), campo='apellido')

    def clean_email(self):
        email = validar_correo(self.cleaned_data.get('email', ''))
        if Usuario.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ese correo electrónico ya está registrado.')
        return email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise ValidationError('Debes escribir el nombre de usuario.')
        if len(username) < 3:
            raise ValidationError('El nombre de usuario debe tener al menos 3 caracteres.')
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError('Ese nombre de usuario ya está en uso.')
        return username

    def clean_password(self):
        return validar_password(
            self.cleaned_data.get('password', ''),
            usuario=self.cleaned_data.get('username', ''),
        )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password2 = cleaned_data.get('password2')
        if password and password2 and password != password2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned_data