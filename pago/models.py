from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models

# Límites del monto inicial al abrir una caja (en pesos colombianos)
MONTO_INICIAL_MIN = Decimal('200000')
MONTO_INICIAL_MAX = Decimal('1000000')


class Caja(models.Model):
    ESTADO_CAJA_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    ]
    id             = models.AutoField(primary_key=True)
    monto_inicial  = models.DecimalField(
                        max_digits=10,
                        decimal_places=2,
                        validators=[
                            MinValueValidator(
                                MONTO_INICIAL_MIN,
                                'El monto inicial mínimo es de $200.000.'
                            ),
                            MaxValueValidator(
                                MONTO_INICIAL_MAX,
                                'El monto inicial máximo es de $1.000.000.'
                            ),
                        ],
                     )
    cajero         = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.CASCADE,
                        related_name='cajas',
                        verbose_name='Cajero'
                     )
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre   = models.DateTimeField(null=True, blank=True)
    estado         = models.CharField(
                        max_length=10,
                        choices=ESTADO_CAJA_CHOICES,
                        default='ABIERTA'
                     )
    observaciones  = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha_apertura']
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        cajero_str = self.cajero.username if self.cajero else "Sin Cajero"
        return f'Caja #{self.pk} – {cajero_str} – {self.get_estado_display()}'


class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
    ]
    id          = models.AutoField(primary_key=True)
    pedido      = models.ForeignKey(
                    'pedidos.Pedido',
                    on_delete=models.CASCADE,
                    related_name='pagos',
                    verbose_name='Pedido'
                  )
    caja        = models.ForeignKey(
                    Caja,
                    on_delete=models.CASCADE,
                    related_name='pagos',
                    verbose_name='Caja'
                  )
    metodo_pago = models.CharField(
                    max_length=50,
                    choices=METODO_PAGO_CHOICES,
                    default='EFECTIVO'
                  )
    monto       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    referencia  = models.CharField(max_length=100, blank=True, default='')
    fecha_pago  = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, default='')
    # ★ NUEVO: baucher / comprobante (foto o PDF) para pagos con tarjeta o transferencia
    comprobante = models.FileField(upload_to='comprobantes/%Y/%m/', blank=True, null=True)

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago #{self.pk} – ${self.monto}'