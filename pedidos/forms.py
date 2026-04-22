from django import forms
from .models import Pedido, Orden, Pago, Caja


class PedidoForm(forms.ModelForm):
    class Meta:
        model  = Pedido
        fields = ['cliente', 'descripcion', 'estado', 'total']
        widgets = {
            'cliente':     forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del cliente'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción...'}),
            'estado':      forms.Select(attrs={'class': 'form-select'}),
            'total':       forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }


class OrdenForm(forms.ModelForm):
    class Meta:
        model  = Orden
        fields = ['pedido', 'estado', 'subtotal', 'impuesto', 'notas']
        widgets = {
            'pedido':   forms.Select(attrs={'class': 'form-select'}),
            'estado':   forms.Select(attrs={'class': 'form-select'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'impuesto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'notas':    forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class PagoForm(forms.ModelForm):
    class Meta:
        model  = Pago
        fields = ['orden', 'metodo', 'monto', 'referencia', 'estado']
        widgets = {
            'orden':      forms.Select(attrs={'class': 'form-select'}),
            'metodo':     forms.Select(attrs={'class': 'form-select'}),
            'monto':      forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'referencia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nro. de referencia'}),
            'estado':     forms.Select(attrs={'class': 'form-select'}),
        }


class CajaForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['nombre', 'saldo_inicial', 'observaciones']
        widgets = {
            'nombre':        forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Caja 1'}),
            'saldo_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class CajaCierreForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['saldo_final', 'observaciones']
        widgets = {
            'saldo_final':   forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }