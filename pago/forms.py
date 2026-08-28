from django import forms
from django.core.exceptions import ValidationError

from .models import Pago, Caja

_INPUT = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)


class PagoForm(forms.ModelForm):
    class Meta:
        model  = Pago
        fields = ['pedido', 'metodo_pago', 'monto', 'referencia', 'descripcion']
        widgets = {
            'pedido':      forms.Select(attrs={'style': _INPUT}),
            'metodo_pago': forms.Select(attrs={'style': _INPUT}),
            'monto':       forms.HiddenInput(),
            'referencia':  forms.TextInput(attrs={'style': _INPUT, 'placeholder': 'Nro. de referencia (opcional)'}),
            'descripcion': forms.Textarea(attrs={'style': _INPUT + 'resize:vertical;min-height:80px;', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['monto'].required = False
        self.fields['referencia'].required = False

    def clean_pedido(self):
        pedido = self.cleaned_data.get('pedido')
        if not pedido:
            raise ValidationError('Debes seleccionar un pedido.')
        return pedido

    def clean_metodo_pago(self):
        metodo = self.cleaned_data.get('metodo_pago')
        if not metodo:
            raise ValidationError('Debes seleccionar un método de pago.')
        return metodo

    def clean_monto(self):
        monto = self.cleaned_data.get('monto')
        if monto is None:
            raise ValidationError('El monto es obligatorio.')
        if monto <= 0:
            raise ValidationError('El monto debe ser mayor que cero.')
        return monto

    def clean_referencia(self):
        referencia = self.cleaned_data.get('referencia', '').strip()
        metodo = self.cleaned_data.get('metodo_pago')
        if metodo and metodo != 'EFECTIVO' and not referencia:
            raise ValidationError('La referencia es obligatoria para pagos con tarjeta o transferencia.')
        return referencia

    def clean(self):
        cleaned_data = super().clean()
        monto = cleaned_data.get('monto')
        pedido = cleaned_data.get('pedido')

        if pedido and monto:
            # Validar que el monto no supere el total del pedido
            if monto > pedido.total:
                raise ValidationError('El monto del pago no puede superar el total del pedido.')

        return cleaned_data


class CajaForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['monto_inicial', 'cajero', 'observaciones']
        widgets = {
            'monto_inicial': forms.NumberInput(attrs={
                'style': _INPUT,
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'cajero': forms.Select(attrs={'style': _INPUT}),
            'observaciones': forms.Textarea(attrs={
                'style': _INPUT + 'resize:vertical;min-height:80px;',
                'rows': 3,
                'placeholder': 'Notas u observaciones sobre la apertura... (opcional)',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['observaciones'].required = False
        self.fields['cajero'].required = True

    def clean_monto_inicial(self):
        monto = self.cleaned_data.get('monto_inicial')
        if monto is None:
            raise ValidationError('El monto inicial es obligatorio.')
        if monto < 0:
            raise ValidationError('El monto inicial no puede ser negativo.')
        return monto

    def clean_cajero(self):
        cajero = self.cleaned_data.get('cajero')
        if not cajero:
            raise ValidationError('Debes seleccionar un cajero.')
        return cajero
