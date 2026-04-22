from django.db import models
from django.conf import settings
from django.utils import timezone


class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_proceso',  'En Proceso'),
        ('completado',  'Completado'),
        ('cancelado',   'Cancelado'),
    ]
    cliente       = models.CharField(max_length=200)
    descripcion   = models.TextField(blank=True)
    estado        = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    total         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_por    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pedidos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mod_pedido'
        ordering = ['-fecha_creacion']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f'Pedido #{self.pk} - {self.cliente}'


class Orden(models.Model):
    ESTADO_CHOICES = [
        ('abierta',    'Abierta'),
        ('procesando', 'Procesando'),
        ('pagada',     'Pagada'),
        ('anulada',    'Anulada'),
    ]
    pedido        = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='ordenes')
    numero_orden  = models.CharField(max_length=50, unique=True)
    estado        = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierta')
    subtotal      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total         = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notas         = models.TextField(blank=True)
    creada_en     = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mod_orden'
        ordering = ['-creada_en']
        verbose_name = 'Orden'
        verbose_name_plural = 'Órdenes'

    def __str__(self):
        return f'Orden {self.numero_orden}'

    def save(self, *args, **kwargs):
        self.total = self.subtotal + self.impuesto
        super().save(*args, **kwargs)


class Pago(models.Model):
    METODO_CHOICES = [
        ('efectivo',       'Efectivo'),
        ('tarjeta_credito','Tarjeta de Crédito'),
        ('tarjeta_debito', 'Tarjeta de Débito'),
        ('transferencia',  'Transferencia'),
        ('nequi',          'Nequi'),
        ('daviplata',      'Daviplata'),
    ]
    ESTADO_CHOICES = [
        ('pendiente',  'Pendiente'),
        ('aprobado',   'Aprobado'),
        ('rechazado',  'Rechazado'),
        ('reembolsado','Reembolsado'),
    ]
    orden         = models.ForeignKey(Orden, on_delete=models.CASCADE, related_name='pagos')
    metodo        = models.CharField(max_length=30, choices=METODO_CHOICES)
    monto         = models.DecimalField(max_digits=12, decimal_places=2)
    referencia    = models.CharField(max_length=100, blank=True)
    estado        = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    fecha_pago    = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mod_pago'
        ordering = ['-fecha_pago']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f'Pago #{self.pk} - {self.get_metodo_display()} ${self.monto}'


class Caja(models.Model):
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]
    nombre          = models.CharField(max_length=100)
    responsable     = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cajas')
    saldo_inicial   = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_final     = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado          = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='abierta')
    fecha_apertura  = models.DateTimeField(default=timezone.now)
    fecha_cierre    = models.DateTimeField(null=True, blank=True)
    observaciones   = models.TextField(blank=True)

    class Meta:
        db_table = 'mod_caja'
        ordering = ['-fecha_apertura']
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f'Caja {self.nombre} - {self.get_estado_display()}'