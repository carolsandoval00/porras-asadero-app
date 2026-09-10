import re

from django import forms
from django.core.exceptions import ValidationError

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

# ─── Validadores reutilizables ─────────────────────────────────
def _solo_numeros(value, longitud=None, campo='campo'):
    """Valida que el valor contenga solo dígitos y opcionalmente una longitud exacta."""
    if not value:
        raise ValidationError(f'El {campo} es obligatorio.')
    texto = str(value).strip()
    if not texto.isdigit():
        raise ValidationError(f'El {campo} debe contener solo números.')
    if longitud and len(texto) != longitud:
        raise ValidationError(f'El {campo} debe tener exactamente {longitud} dígitos.')
    return texto


def _solo_letras(value, campo='campo', max_length=100):
    """Valida que el valor contenga solo letras y sea un texto razonable."""
    if not value:
        raise ValidationError(f'El {campo} es obligatorio.')
    texto = str(value).strip()

    if len(texto) < 2:
        raise ValidationError(f'El {campo} debe tener al menos 2 caracteres.')
    if len(texto) > max_length:
        raise ValidationError(f'El {campo} no puede superar {max_length} caracteres.')

    if not re.fullmatch(r'[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ\s]+', texto):
        raise ValidationError(f'El {campo} solo puede contener letras y espacios.')

    if len(set(texto.replace(' ', ''))) < 2:
        raise ValidationError(f'El {campo} no puede ser un solo carácter repetido.')

    if not re.search(r'[aeiouáéíóúüAEIOUÁÉÍÓÚÜ]', texto):
        raise ValidationError(f'El {campo} debe incluir al menos una vocal.')

    return texto


def _validar_palabras(value, campo='nombre_completo', min_palabras=2, max_length=255):
    """Valida un texto que debe contener al menos N palabras (ej. nombre y apellido)."""
    texto = _solo_letras(value, campo=campo, max_length=max_length)
    palabras = texto.split()
    if len(palabras) < min_palabras:
        raise ValidationError(f'El {campo} debe incluir nombre y apellido (mínimo {min_palabras} palabras).')
    return texto


def _precio_positivo(value):
    """Valida que el precio sea mayor que cero."""
    if value is None or value <= 0:
        raise ValidationError('El precio debe ser mayor que cero.')
    return value


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

    def clean_subtotal(self):
        subtotal = self.cleaned_data.get('subtotal')
        if subtotal is not None and subtotal < 0:
            raise ValidationError('El subtotal no puede ser negativo.')
        return subtotal

    def clean_impuestos(self):
        impuestos = self.cleaned_data.get('impuestos')
        if impuestos is not None and impuestos < 0:
            raise ValidationError('Los impuestos no pueden ser negativos.')
        return impuestos

    def clean_total(self):
        total = self.cleaned_data.get('total')
        if total is not None and total < 0:
            raise ValidationError('El total no puede ser negativo.')
        return total


# ─── Formulario de Producto ────────────────────────────────────
class ProductoForm(forms.ModelForm):
    class Meta:
        model  = Producto
        fields = ['nombre', 'categoria', 'precio', 'descripcion']
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

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre del producto es obligatorio.')
        return _solo_letras(nombre, campo='nombre del producto')

    def clean_precio(self):
        precio = self.cleaned_data.get('precio')
        return _precio_positivo(precio)

    def clean_categoria(self):
        categoria = self.cleaned_data.get('categoria')
        if not categoria:
            raise ValidationError('Debes seleccionar una categoría.')
        return categoria


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

    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre', '').strip()
        if not nombre:
            raise ValidationError('El nombre de la categoría es obligatorio.')
        if Categoria.objects.filter(nombre__iexact=nombre).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise ValidationError('Ya existe una categoría con ese nombre.')
        return _solo_letras(nombre, campo='nombre de la categoría')


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

    def clean_nombre_completo(self):
        nombre = self.cleaned_data.get('nombre_completo', '').strip()
        return _validar_palabras(nombre, campo='nombre completo', min_palabras=2)

    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        return _solo_numeros(telefono, longitud=10, campo='teléfono')

    def clean_documento(self):
        documento = self.cleaned_data.get('documento')
        return _solo_numeros(documento, campo='documento')

    def clean_tipo_documento(self):
        tipo = self.cleaned_data.get('tipo_documento')
        if not tipo:
            raise ValidationError('Debes seleccionar un tipo de documento.')
        return tipo
