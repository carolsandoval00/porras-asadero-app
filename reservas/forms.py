import re
from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from .models import Mesa, Reserva

INPUT_STYLE = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)


# ─── Formulario de Mesa ────────────────────────────────────────
class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero_mesa', 'capacidad', 'ubicacion', 'estado']
        widgets = {
            'numero_mesa': forms.NumberInput(attrs={
                'style': INPUT_STYLE, 'min': 1, 'placeholder': 'Ej: 7',
            }),
            'capacidad': forms.NumberInput(attrs={
                'style': INPUT_STYLE, 'min': 1, 'max': 30, 'placeholder': 'Ej: 4',
            }),
            'ubicacion': forms.TextInput(attrs={
                'style': INPUT_STYLE, 'placeholder': 'Ej: Salón principal',
            }),
            'estado': forms.Select(attrs={'style': INPUT_STYLE}),
        }

    def clean_numero_mesa(self):
        numero = self.cleaned_data.get('numero_mesa')
        if numero is None:
            raise ValidationError('El número de mesa es obligatorio.')
        if numero <= 0:
            raise ValidationError('El número de mesa debe ser mayor que cero.')
        return numero

    def clean_capacidad(self):
        capacidad = self.cleaned_data.get('capacidad')
        if capacidad is None:
            raise ValidationError('La capacidad es obligatoria.')
        if capacidad <= 0:
            raise ValidationError('La capacidad debe ser mayor que cero.')
        if capacidad > 30:
            raise ValidationError('La capacidad máxima permitida es de 30 personas.')
        return capacidad

    def clean_ubicacion(self):
        ubicacion = (self.cleaned_data.get('ubicacion') or '').strip()
        if not ubicacion:
            raise ValidationError('La ubicación es obligatoria.')
        return ubicacion


# ─── Formulario de Reserva ─────────────────────────────────────
class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = [
            'nombre_cliente', 'telefono', 'email',
            'fecha_reserva', 'hora_reserva', 'numero_personas',
            'ocasion', 'estado', 'notas', 'numero_mesa',
        ]
        widgets = {
            'nombre_cliente': forms.TextInput(attrs={
                'style': INPUT_STYLE, 'placeholder': 'Ej: María García'}),
            'telefono': forms.TextInput(attrs={
                'style': INPUT_STYLE, 'placeholder': '3001234567', 'maxlength': 10}),
            'email': forms.EmailInput(attrs={
                'style': INPUT_STYLE, 'placeholder': 'correo@ejemplo.com'}),
            'fecha_reserva': forms.DateInput(attrs={'type': 'date', 'style': INPUT_STYLE}),
            'hora_reserva': forms.TimeInput(attrs={'type': 'time', 'style': INPUT_STYLE}),
            'numero_personas': forms.NumberInput(attrs={
                'style': INPUT_STYLE, 'min': 1, 'max': 30}),
            'ocasion': forms.TextInput(attrs={'style': INPUT_STYLE}),
            'estado': forms.Select(attrs={'style': INPUT_STYLE}),
            'notas': forms.Textarea(attrs={'style': INPUT_STYLE, 'rows': 3}),
            'numero_mesa': forms.Select(attrs={'style': INPUT_STYLE}),
        }

    def clean_nombre_cliente(self):
        nombre = (self.cleaned_data.get('nombre_cliente') or '').strip()
        if not nombre:
            raise ValidationError('El nombre del cliente es obligatorio.')
        return nombre

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()
        if not telefono:
            raise ValidationError('El teléfono es obligatorio.')
        if not re.fullmatch(r'\d{10}', telefono):
            raise ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        return telefono

    def clean_fecha_reserva(self):
        fecha = self.cleaned_data.get('fecha_reserva')
        if not fecha:
            raise ValidationError('La fecha de la reserva es obligatoria.')
        # Solo se valida al crear: una reserva pasada se puede seguir editando.
        if self.instance.pk is None and fecha < date.today():
            raise ValidationError('No se pueden crear reservas en fechas pasadas.')
        return fecha

    def clean_hora_reserva(self):
        hora = self.cleaned_data.get('hora_reserva')
        if not hora:
            raise ValidationError('La hora de la reserva es obligatoria.')
        return hora

    def clean_numero_personas(self):
        personas = self.cleaned_data.get('numero_personas')
        if personas is None:
            raise ValidationError('El número de personas es obligatorio.')
        if personas <= 0:
            raise ValidationError('El número de personas debe ser mayor que cero.')
        if personas > 30:
            raise ValidationError('El número máximo de personas por reserva es 30.')
        return personas

    def clean_numero_mesa(self):
        mesa = self.cleaned_data.get('numero_mesa')
        if not mesa:
            raise ValidationError('Debes seleccionar una mesa.')
        return mesa

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha_reserva')
        hora = cleaned_data.get('hora_reserva')
        mesa = cleaned_data.get('numero_mesa')
        estado = cleaned_data.get('estado')
        personas = cleaned_data.get('numero_personas')

        if fecha and hora and mesa and estado != 'CANCELADA':
            # La mesa no puede tener otra reserva activa en la misma franja horaria.
            desde_hora = hora.replace(minute=0, second=0, microsecond=0)
            hasta_hora = hora.replace(minute=59, second=59, microsecond=0)

            conflictos = Reserva.objects.filter(
                numero_mesa=mesa,
                fecha_reserva=fecha,
                hora_reserva__range=(desde_hora, hasta_hora),
                estado__in=['PENDIENTE', 'CONFIRMADA'],
            )
            if self.instance.pk:
                conflictos = conflictos.exclude(pk=self.instance.pk)

            if conflictos.exists():
                raise ValidationError('Esa mesa ya está reservada para ese día y hora.')

        if mesa and personas and personas > mesa.capacidad:
            raise ValidationError(
                f'La mesa {mesa.numero_mesa} tiene capacidad para {mesa.capacidad} personas.'
            )

        return cleaned_data