from django.db import models


METODO_CHOICES = [
    ('efectivo',      'Efectivo'),
    ('tarjeta',       'Tarjeta'),
    ('transferencia', 'Transferencia'),
    ('nequi',         'Nequi'),
    ('daviplata',     'Daviplata'),
]

ESTADO_CHOICES = [
    ('pendiente',    'Pendiente'),
    ('aprobado',     'Aprobado'),
    ('rechazado',    'Rechazado'),
    ('reembolsado',  'Reembolsado'),
]


class Pago(models.Model):
    metodo_pago = models.CharField(max_length=50, choices=METODO_CHOICES, default='efectivo')
    monto       = models.DecimalField(max_digits=10, decimal_places=2)
    referencia  = models.CharField(max_length=100, blank=True, default='')
    estado      = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago  = models.DateTimeField(auto_now_add=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-fecha_pago']

    def __str__(self):
        return f'Pago #{self.pk} – ${self.monto}'