from django import forms
from .models import Pago

_INPUT = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)

class PagoForm(forms.ModelForm):
    class Meta:
        model  = Pago
        fields = ['orden', 'metodo_pago', 'monto', 'referencia', 'estado', 'descripcion']
        widgets = {
            'orden':       forms.Select(attrs={'style': _INPUT}),
            'metodo_pago': forms.Select(attrs={'style': _INPUT}),
            'monto':       forms.HiddenInput(),  # se llena automáticamente desde la orden
            'referencia':  forms.TextInput(attrs={'style': _INPUT, 'placeholder': 'Nro. de referencia (opcional)'}),
            'estado':      forms.Select(attrs={'style': _INPUT}),
            'descripcion': forms.Textarea(attrs={'style': _INPUT + 'resize:vertical;min-height:80px;', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['monto'].required = False