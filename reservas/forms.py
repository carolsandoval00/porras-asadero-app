from datetime import date

from django import forms
from django.core.exceptions import ValidationError

from .models import Mesa, Reserva

# ─── Formulario de Mesa ────────────────────────────────────────
class MesaForm(forms.ModelForm):
    class Meta:
        model = Mesa
        fields = ['numero_mesa', 'capacidad', 'ubicacion', 'estado']
        widgets = {
            'numero_mesa': forms.NumberInput(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
                'min': 1,
                'placeholder': 'Ej: 7',
            }),
            'capacidad': forms.NumberInput(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
                'min': 1,
                'max': 30,
                'placeholder': 'Ej: 4',
            }),
            'ubicacion': forms.TextInput(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
                'placeholder': 'Ej: Salón principal',
            }),
            'estado': forms.Select(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
            }),
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
        ubicacion = self.cleaned_data.get('ubicacion', '').strip()
        if not ubicacion:
            raise ValidationError('La ubicación es obligatoria.')
        return ubicacion


# ─── Formulario de Reserva ─────────────────────────────────────
class ReservaForm(forms.ModelForm):
    class Meta:
        model = Reserva
        fields = ['fecha_reserva', 'hora_reserva', 'numero_personas', 'estado', 'cliente', 'numero_mesa']
        widgets = {
            'fecha_reserva': forms.DateInput(attrs={
                'type': 'date',
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
            }),
            'hora_reserva': forms.TimeInput(attrs={
                'type': 'time',
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
            }),
            'numero_personas': forms.NumberInput(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
                'min': 1,
                'max': 30,
            }),
            'estado': forms.Select(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
            }),
            'cliente': forms.Select(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
            }),
            'numero_mesa': forms.Select(attrs={
                'style': 'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
                         'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
                         'box-sizing:border-box;font-family:inherit;',
            }),
        }

    def clean_fecha_reserva(self):
        fecha = self.cleaned_data.get('fecha_reserva')
        if not fecha:
            raise ValidationError('La fecha de la reserva es obligatoria.')
        if fecha < date.today():
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

        if fecha and hora and mesa:
            # Validar que la mesa no esté reservada en la misma fecha y hora
            desde_hora = hora.replace(minute=0, second=0, microsecond=0)
            hasta_hora = hora.replace(minute=59, second=59, microsecond=0)

            reservas_conflictivas = Reserva.objects.filter(
                numero_mesa=mesa,
                fecha_reserva=fecha,
                hora_reserva__range=(desde_hora, hasta_hora),
                estado__in=['PENDIENTE', 'CONFIRMADA'],
            )
            if self.instance.pk:
                reservas_conflictivas = reservas_conflictivas.exclude(pk=self.instance.pk)

            if reservas_conflictivas.exists():
                raise ValidationError('Esa mesa ya está reservada para ese día y hora.')

            # Validar que la capacidad de la mesa sea suficiente
            if mesa.capacidad and cleaned_data.get('numero_personas'):
                if cleaned_data['numero_personas'] > mesa.capacidad:
                    raise ValidationError(
                        f'La mesa {mesa.numero_mesa} tiene capacidad para {mesa.capacidad} personas.'
                    )

        return cleaned_data
