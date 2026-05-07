from django.db import models

METODO_CHOICES = [
    ('efectivo',      'Efectivo'),
    ('transferencia', 'Transferencia'),

]

ESTADO_CHOICES = [
    ('pendiente',   'Pendiente'),
    ('aprobado',    'Aprobado'),
 
]


class Pago(models.Model):
    orden       = models.ForeignKey(
                    'pedidos.Orden',
                    on_delete=models.SET_NULL,
                    null=True, blank=True,
                    related_name='pagos'
                  )
    metodo_pago = models.CharField(max_length=50, choices=METODO_CHOICES, default='efectivo')
    monto       = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    referencia  = models.CharField(max_length=100, blank=True, default='')
    estado      = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago  = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago #{self.pk} – ${self.monto}'