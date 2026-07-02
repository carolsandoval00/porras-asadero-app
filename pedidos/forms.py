from django import forms
from .models import Pedido, Producto, Categoria
from usuarios.models import Cliente

# ─── Estilo base reutilizable ──────────────────────────────────
_INPUT = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)
_SELECT   = _INPUT
_TEXTAREA = _INPUT + 'resize:vertical;min-height:80px;'

# ─── Formulario de Pedido ──────────────────────────────────────
class PedidoForm(forms.ModelForm):
    class Meta:
        model  = Pedido
        fields = ['cliente', 'mesa', 'tipo_pedido', 'subtotal', 'impuestos', 'total', 'descripcion']
        widgets = {
            'cliente': forms.Select(attrs={'style': _SELECT}),
            'mesa': forms.Select(attrs={'style': _SELECT}),
            'tipo_pedido': forms.Select(attrs={'style': _SELECT}),
            'estado': forms.Select(attrs={'style': _SELECT}),
            'subtotal': forms.NumberInput(attrs={'style': _INPUT, 'step': '0.01', 'placeholder': '0.00'}),
            'impuestos': forms.NumberInput(attrs={'style': _INPUT, 'step': '0.01', 'placeholder': '0.00'}),
            'total': forms.NumberInput(attrs={'style': _INPUT, 'step': '0.01', 'placeholder': '0.00'}),
            'descripcion': forms.Textarea(attrs={'style': _TEXTAREA, 'rows': 2, 'placeholder': 'Notas/Descripción...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].required = False
        self.fields['mesa'].required = False
        self.fields['subtotal'].required = False
        self.fields['impuestos'].required = False
        self.fields['total'].required = False

# ─── Formulario de Producto ────────────────────────────────────
class ProductoForm(forms.ModelForm):
    class Meta:
        model  = Producto
        fields = ['nombre', 'categoria', 'precio', 'descripcion' ]
        widgets = {
            'nombre': forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: Trucha a la plancha',
            }),
            'categoria': forms.Select(attrs={'style': _SELECT}),
            'precio':     forms.NumberInput(attrs={
                'style': _INPUT, 'step': '0.01', 'placeholder': '0.00',
            }),
            'descripcion': forms.Textarea(attrs={
                'style': _TEXTAREA,
                'rows': 2,
                'placeholder': 'Descripción opcional...',
            }),
            
        }

# ─── Formulario de Categoría ───────────────────────────────────
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: Carnes al Carbón, Bebidas',
            }),
            'descripcion': forms.Textarea(attrs={
                'style': _TEXTAREA,
                'rows': 2,
                'placeholder': 'Descripción opcional...',
            }),
        }

# ─── Formulario de Cliente ─────────────────────────────────────
class ClienteForm(forms.ModelForm):
    TIPO_DOCUMENTO_CHOICES = [
        ('CC', 'Cédula de Ciudadanía'),
        ('CE', 'Cédula de Extranjería'),
        ('TI', 'Tarjeta de Identidad'),
        ('PP', 'Pasaporte'),
    ]
    tipo_documento = forms.ChoiceField(
        choices=TIPO_DOCUMENTO_CHOICES,
        widget=forms.Select(attrs={'style': _SELECT})
    )

    class Meta:
        model = Cliente
        fields = ['nombre_completo', 'telefono', 'tipo_documento', 'documento', 'direccion']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: Andrés Rojas',
            }),
            'telefono': forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: 3204567890',
            }),
            'documento': forms.TextInput(attrs={
                'style': _INPUT,
                'placeholder': 'Ej: 1057888999',
            }),
            'direccion': forms.Textarea(attrs={
                'style': _TEXTAREA,
                'rows': 2,
                'placeholder': 'Dirección opcional...',
            }),
        }
