from django import forms
from .models import Pago


class PagoForm(forms.ModelForm):
    class Meta:
        model  = Pago
        fields = ['metodo_pago', 'monto', 'referencia', 'estado', 'descripcion']
        widgets = {
            'metodo_pago': forms.Select(attrs={'class': 'form-select'}),
            'monto':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'referencia':  forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nro. de referencia (opcional)'}),
            'estado':      forms.Select(attrs={'class': 'form-select'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción opcional...'}),
        }