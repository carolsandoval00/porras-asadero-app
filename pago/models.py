from decimal import Decimal
from django.db import models, transaction
from django.db.models import Max
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.conf import settings

class Caja(models.Model):
    ESTADO_CAJA_CHOICES = [
        ('ABIERTA', 'Abierta'),
        ('CERRADA', 'Cerrada'),
    ]
    id             = models.AutoField(primary_key=True)
    monto_inicial  = models.DecimalField(max_digits=10, decimal_places=2)
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

    @property
    def numero(self):
        """Número consecutivo de la caja según el orden de apertura: 01, 02, 03..."""
        n = Caja.objects.filter(pk__lt=self.pk).count() + 1
        return f'{n:02d}'

    def __str__(self):
        cajero_str = self.cajero.username if self.cajero else "Sin Cajero"
        return f'Caja #{self.pk} – {cajero_str} – {self.get_estado_display()}'


class Pago(models.Model):
    METODO_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA', 'Tarjeta'),
        ('TRANSFERENCIA', 'Transferencia'),
    ]
    id            = models.AutoField(primary_key=True)
    # Número de recibo consecutivo (1, 2, 3...), independiente del id
    numero_recibo = models.PositiveIntegerField(
                      unique=True,
                      null=True,
                      blank=True,
                      editable=False,
                      verbose_name='Número de recibo'
                    )
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
    comprobante = models.ImageField(
                    upload_to='comprobantes/%Y/%m/',
                    blank=True,
                    null=True,
                    verbose_name='Foto del comprobante'
                  )
    fecha_pago  = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha_pago']

    def save(self, *args, **kwargs):
        # Al crear el pago, asigna el siguiente número de recibo
        if self.numero_recibo is None:
            with transaction.atomic():
                ultimo = Pago.objects.aggregate(m=Max('numero_recibo'))['m'] or 0
                self.numero_recibo = ultimo + 1
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'Recibo #{self.numero_recibo or self.pk} – ${self.monto}'