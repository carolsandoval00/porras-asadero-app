from django import forms
from .models import Pedido, Orden, Producto, Caja

# ─── Estilo base reutilizable (no depende de Bootstrap) ───────
_INPUT = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)
_SELECT = _INPUT
_TEXTAREA = _INPUT + 'resize:vertical;min-height:80px;'


class PedidoForm(forms.ModelForm):
    class Meta:
        model  = Pedido
        fields = ['cliente', 'descripcion', 'estado', 'total']
        widgets = {
            'cliente':     forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Nombre del cliente',
            }),
            'descripcion': forms.Textarea(attrs={
                'style': _TEXTAREA,
                'rows': 3,
                'placeholder': 'Descripción del pedido...',
            }),
            'estado':       forms.Select(attrs={'style': _SELECT}),
            'total':       forms.NumberInput(attrs={
                'style': _INPUT,
                'step': '0.01',
                'placeholder': '0.00',
            }),
        }


class OrdenForm(forms.ModelForm):
    class Meta:
        model  = Orden
        # Se agrega 'producto' a los campos para permitir la selección y actualización automática
        fields = ['pedido', 'producto', 'estado', 'subtotal', 'impuesto', 'notas']
        widgets = {
            'pedido':   forms.Select(attrs={'style': _SELECT}),
            # Nuevo widget para el selector de productos con el estilo de la app
            'producto': forms.Select(attrs={'style': _SELECT}),
            'estado':   forms.Select(attrs={'style': _SELECT}),
            'subtotal': forms.NumberInput(attrs={
                'style': _INPUT, 'step': '0.01', 'placeholder': '0.00',
            }),
            'impuesto': forms.NumberInput(attrs={
                'style': _INPUT, 'step': '0.01', 'placeholder': '0.00',
            }),
            'notas':    forms.Textarea(attrs={
                'style': _TEXTAREA, 'rows': 2, 'placeholder': 'Notas adicionales...',
            }),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model  = Producto
        fields = ['nombre', 'categoria', 'precio', 'descripcion', 'disponible']
        widgets = {
            'nombre':      forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: Trucha a la plancha',
            }),
            'categoria':   forms.Select(attrs={'style': _SELECT}),
            'precio':      forms.NumberInput(attrs={
                'style': _INPUT, 'step': '0.01', 'placeholder': '0.00',
            }),
            'descripcion': forms.Textarea(attrs={
                'style': _TEXTAREA,
                'rows': 2,
                'placeholder': 'Descripción opcional...',
            }),
            'disponible':  forms.CheckboxInput(attrs={
                'style': 'width:18px;height:18px;accent-color:#C0392B;cursor:pointer;',
            }),
        }


class CajaForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['nombre', 'saldo_inicial', 'observaciones']
        widgets = {
            'nombre':        forms.TextInput(attrs={
                'style': _INPUT, 'placeholder': 'Ej: Caja Principal',
            }),
            'saldo_inicial': forms.NumberInput(attrs={
                'style': _INPUT, 'step': '0.01', 'placeholder': '0.00',
            }),
            'observaciones': forms.Textarea(attrs={
                'style': _TEXTAREA, 'rows': 2,
            }),
        }


class CajaCierreForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['saldo_final', 'observaciones']
        widgets = {
            'saldo_final':   forms.NumberInput(attrs={
                'style': _INPUT, 'step': '0.01', 'placeholder': '0.00',
            }),
            'observaciones': forms.Textarea(attrs={
                'style': _TEXTAREA, 'rows': 2,
            }),
        }