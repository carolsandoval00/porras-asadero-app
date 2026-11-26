from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q

from pedidos.models import Pedido

from .models import Pago, Caja

MAX_FOTO_BYTES = 8 * 1024 * 1024  # 8 MB

# Límites del monto inicial al abrir caja (pesos)
MONTO_INICIAL_MIN = Decimal('100000')
MONTO_INICIAL_MAX = Decimal('1000000')
MAX_OBSERVACIONES = 500

_INPUT = (
    'width:100%;padding:.55rem .85rem;border:1px solid #D4C4A0;'
    'border-radius:8px;font-size:.9rem;color:#1A1008;background:#FDF7EC;'
    'box-sizing:border-box;font-family:inherit;'
)


class PagoForm(forms.ModelForm):
    class Meta:
        model  = Pago
        fields = ['pedido', 'metodo_pago', 'monto', 'comprobante', 'descripcion']
        widgets = {
            'pedido':      forms.Select(attrs={'style': _INPUT}),
            'metodo_pago': forms.Select(attrs={'style': _INPUT}),
            'monto':       forms.HiddenInput(),
            # En celulares/tablets abre la cámara trasera; en PC abre el selector de archivos.
            # Se oculta visualmente: la tarjeta bonita de subida la dibuja el template (clase pg-upload).
            'comprobante': forms.FileInput(attrs={
                'accept': 'image/*',
                'capture': 'environment',
                'id': 'id_comprobante',
                'class': 'pg-upload-input',
            }),
            'descripcion': forms.Textarea(attrs={'style': _INPUT + 'resize:vertical;min-height:80px;', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['monto'].required = False
        self.fields['comprobante'].required = False

        # Solo Efectivo y Transferencia (Tarjeta ya no se ofrece al registrar pagos;
        # los pagos antiguos con tarjeta se siguen mostrando normal).
        self.fields['metodo_pago'].choices = [
            (valor, texto) for valor, texto in Pago.METODO_PAGO_CHOICES if valor != 'TARJETA'
        ]

        # Solo órdenes sin pagar, y con cliente cargado en la misma consulta.
        self.fields['pedido'].queryset = (
            Pedido.objects.exclude(estado='PAGADO').select_related('cliente')
        )
        # Muestra el mismo número de orden que se ve en la tabla (03, 02...)
        # en lugar del id interno de la base de datos (#1009).
        self.fields['pedido'].label_from_instance = self._etiqueta_pedido

    @staticmethod
    def _etiqueta_pedido(pedido):
        cliente = pedido.cliente.nombre_completo if pedido.cliente else 'Cliente de Paso'
        return f'Pedido #{pedido.numero_orden} - {cliente}'

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

    def clean_comprobante(self):
        foto = self.cleaned_data.get('comprobante')
        if foto and hasattr(foto, 'size') and foto.size > MAX_FOTO_BYTES:
            raise ValidationError('La foto es demasiado pesada (máximo 8 MB).')
        return foto

    def clean(self):
        cleaned_data = super().clean()
        monto = cleaned_data.get('monto')
        pedido = cleaned_data.get('pedido')

        # Transferencia: la foto del comprobante es obligatoria.
        if cleaned_data.get('metodo_pago') == 'TRANSFERENCIA' and not cleaned_data.get('comprobante'):
            self.add_error('comprobante', 'Debes tomar la foto del comprobante para pagos por transferencia.')

        # Solo se guarda la foto cuando el método es transferencia.
        if cleaned_data.get('metodo_pago') != 'TRANSFERENCIA':
            cleaned_data['comprobante'] = None

        if pedido and monto:
            # Validar que el monto no supere el total del pedido
            if monto > pedido.total:
                raise ValidationError('El monto del pago no puede superar el total del pedido.')

        return cleaned_data


class MontoMilesWidget(forms.TextInput):
    """Campo de monto con puntos de miles (100.000). El navegador los pone
    solos al escribir; aquí se quitan antes de validar para que el servidor
    reciba siempre un número limpio."""

    def value_from_datadict(self, data, files, name):
        valor = data.get(name)
        if isinstance(valor, str):
            valor = valor.replace('$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return valor

    def format_value(self, value):
        if value in (None, ''):
            return ''
        try:
            numero = Decimal(str(value))
        except Exception:
            return str(value)
        if numero == numero.to_integral_value():
            return f'{int(numero):,}'.replace(',', '.')
        return str(value)


class CajaForm(forms.ModelForm):
    class Meta:
        model  = Caja
        fields = ['monto_inicial', 'cajero', 'observaciones']
        widgets = {
            'monto_inicial': MontoMilesWidget(attrs={
                'style': _INPUT,
                'placeholder': '100.000',
                'inputmode': 'numeric',
                'autocomplete': 'off',
                'maxlength': '9',
                'data-miles': '1',
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
        self.fields['observaciones'].widget.attrs['maxlength'] = MAX_OBSERVACIONES

        # Responsable de la caja: solo administradores y cajeros activos
        # (el mismo criterio que decide quién puede entrar al módulo de pagos).
        Usuario = get_user_model()
        campo = self.fields['cajero']
        campo.required = True
        campo.queryset = (
            Usuario.objects.filter(is_active=True)
            .filter(Q(rol__in=['ADMIN', 'CAJERO']) | Q(is_superuser=True))
            .order_by('first_name', 'last_name', 'username')
        )
        campo.empty_label = 'Selecciona un responsable'
        campo.label_from_instance = self._etiqueta_cajero
        campo.error_messages['invalid_choice'] = 'Selecciona un administrador o cajero válido.'

    @staticmethod
    def _etiqueta_cajero(usuario):
        nombre = usuario.get_full_name().strip() or usuario.username
        es_admin = usuario.is_superuser or usuario.rol == 'ADMIN'
        rol = 'Administrador' if es_admin else 'Cajero'
        return f'{nombre} — {rol}'

    def clean_monto_inicial(self):
        monto = self.cleaned_data.get('monto_inicial')
        if monto is None:
            raise ValidationError('El monto inicial es obligatorio.')
        if monto < MONTO_INICIAL_MIN or monto > MONTO_INICIAL_MAX:
            raise ValidationError(
                'El monto inicial debe estar entre $100.000 y $1.000.000.'
            )
        return monto

    def clean_cajero(self):
        cajero = self.cleaned_data.get('cajero')
        if not cajero:
            raise ValidationError('Debes seleccionar un cajero.')
        return cajero

    def clean_observaciones(self):
        observaciones = (self.cleaned_data.get('observaciones') or '').strip()
        if len(observaciones) > MAX_OBSERVACIONES:
            raise ValidationError(
                f'Las observaciones no pueden superar {MAX_OBSERVACIONES} caracteres.'
            )
        return observaciones

    def clean(self):
        cleaned_data = super().clean()
        # Solo puede existir una caja abierta a la vez (se valida en el
        # servidor, no depende de la vista ni del navegador).
        caja_abierta = Caja.objects.filter(estado='ABIERTA').first()
        if caja_abierta:
            raise ValidationError(
                f'Ya hay una caja abierta (Caja #{caja_abierta.numero}). '
                'Debes cerrarla antes de abrir una nueva.'
            )
        return cleaned_data