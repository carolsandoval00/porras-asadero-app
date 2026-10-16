from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

from .models import Pago, Caja, MONTO_INICIAL_MIN, MONTO_INICIAL_MAX

_INPUT = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)


class PagoForm(forms.ModelForm):
    class Meta:
        model  = Pago
        # ★ NUEVO: 'comprobante'
        fields = ['pedido', 'metodo_pago', 'monto', 'referencia', 'descripcion', 'comprobante']
        widgets = {
            'pedido':      forms.Select(attrs={'style': _INPUT}),
            'metodo_pago': forms.Select(attrs={'style': _INPUT}),
            'monto':       forms.HiddenInput(),
            'referencia':  forms.TextInput(attrs={'style': _INPUT, 'placeholder': 'Nro. de referencia (opcional)'}),
            'descripcion': forms.Textarea(attrs={'style': _INPUT + 'resize:vertical;min-height:80px;', 'rows': 2}),
            # ★ NUEVO
            'comprobante': forms.ClearableFileInput(attrs={
                'style': _INPUT,
                'accept': 'image/*,.pdf',
                'id': 'id_comprobante',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['monto'].required = False
        self.fields['referencia'].required = False
        # ★ NUEVO
        self.fields['comprobante'].required = False
        self.fields['comprobante'].validators.append(
            FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp', 'pdf'])
        )

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
        monto       = cleaned_data.get('monto')
        pedido      = cleaned_data.get('pedido')
        metodo      = cleaned_data.get('metodo_pago')
        comprobante = cleaned_data.get('comprobante')

        if pedido and monto:
            # Validar que el monto no supere el total del pedido
            if monto > pedido.total:
                raise ValidationError('El monto del pago no puede superar el total del pedido.')

        # ★ NUEVO: baucher obligatorio con tarjeta o transferencia
        # (si prefieres que sea opcional, borra el bloque "if not comprobante and not ya_tiene")
        if metodo in ('TARJETA', 'TRANSFERENCIA'):
            ya_tiene = self.instance and self.instance.pk and self.instance.comprobante
            if not comprobante and not ya_tiene:
                self.add_error('comprobante', 'Sube el baucher (foto o PDF) del pago.')
            elif comprobante and hasattr(comprobante, 'size') and comprobante.size > 5 * 1024 * 1024:
                self.add_error('comprobante', 'El archivo no puede pesar más de 5 MB.')

        return cleaned_data


class CajaForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['monto_inicial', 'cajero', 'observaciones']
        widgets = {
            'monto_inicial': forms.NumberInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: 200000',
                'step': '100',
                'min': str(MONTO_INICIAL_MIN),
                'max': str(MONTO_INICIAL_MAX),
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
        if monto < MONTO_INICIAL_MIN or monto > MONTO_INICIAL_MAX:
            raise ValidationError(
                'El monto inicial debe estar entre $200.000 y $1.000.000.'
            )
        return monto

    def clean_cajero(self):
        cajero = self.cleaned_data.get('cajero')
        if not cajero:
            raise ValidationError('Debes seleccionar un cajero.')
        return cajero