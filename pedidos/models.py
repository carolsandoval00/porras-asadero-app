from django.db import models
from django.conf import settings
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Contador(models.Model):
    """Contador global para numeración secuencial de pedidos/órdenes."""
    ultimo_numero = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'mod_contador'

    @classmethod
    def siguiente(cls):
        from django.db import transaction
        with transaction.atomic():
            obj, _ = cls.objects.select_for_update().get_or_create(pk=1)
            obj.ultimo_numero += 1
            obj.save()
            return obj.ultimo_numero


class Producto(models.Model):
    CATEGORIA_CHOICES = [
        ('carnes',   'Carnes al Carbón'),
        ('sopas',    'Sopas'),
        ('carta',    'Platos a la Carta'),
        ('bebidas',  'Bebidas'),
        ('otros',    'Otros'),
    ]
    nombre      = models.CharField(max_length=200)
    categoria   = models.CharField(max_length=20, choices=CATEGORIA_CHOICES, default='otros')
    precio      = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    descripcion = models.TextField(blank=True)
    disponible  = models.BooleanField(default=True)
    creado_en   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mod_producto'
        ordering = ['categoria', 'nombre']
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'

    def __str__(self):
        return f'{self.nombre} (${self.precio})'


class Pedido(models.Model):
    ESTADO_CHOICES = [
        ('pendiente',   'Pendiente'),
        ('en_proceso',  'En Proceso'),
        ('completado',  'Completado'),
        ('cancelado',   'Cancelado'),
    ]
    cliente             = models.CharField(max_length=200)
    descripcion         = models.TextField(blank=True)
    estado              = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    total               = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    creado_por          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pedidos')
    fecha_creacion      = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mod_pedido'
        ordering = ['-fecha_creacion']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    def __str__(self):
        return f'Pedido #{self.pk} - {self.cliente}'


class PedidoItem(models.Model):
    pedido          = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto        = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='items')
    cantidad        = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = 'mod_pedido_item'
        verbose_name = 'Item de Pedido'
        verbose_name_plural = 'Items de Pedido'

    def __str__(self):
        return f'{self.cantidad}x {self.producto.nombre}'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


class Orden(models.Model):
    ESTADO_CHOICES = [
        ('abierta',    'Abierta'),
        ('procesando', 'Procesando'),
        ('pagada',     'Pagada'),
        ('anulada',    'Anulada'),
    ]
    pedido       = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='ordenes')
    numero_orden = models.CharField(max_length=50, unique=True)
    estado       = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierta')
    subtotal     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuesto     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total        = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notas        = models.TextField(blank=True)
    creada_en    = models.DateTimeField(auto_now_add=True)

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


class Caja(models.Model):
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('cerrada', 'Cerrada'),
    ]
    nombre         = models.CharField(max_length=100)
    responsable    = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='cajas')
    saldo_inicial  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    saldo_final    = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    estado         = models.CharField(max_length=10, choices=ESTADO_CHOICES, default='abierta')
    fecha_apertura = models.DateTimeField(default=timezone.now)
    fecha_cierre   = models.DateTimeField(null=True, blank=True)
    observaciones  = models.TextField(blank=True)

    class Meta:
        db_table = 'mod_caja'
        ordering = ['-fecha_apertura']
        verbose_name = 'Caja'
        verbose_name_plural = 'Cajas'

    def __str__(self):
        return f'Caja {self.nombre} - {self.get_estado_display()}'


@receiver(post_save, sender=Producto)
def actualizar_ordenes_al_cambiar_producto(sender, instance, **kwargs):
    from django.db.models import Sum, F
    pedidos_con_producto = Pedido.objects.filter(
        items__producto=instance,
        estado='pendiente'
    ).distinct()

    for pedido in pedidos_con_producto:
        pedido.items.filter(producto=instance).update(precio_unitario=instance.precio)
        nuevo_total = sum(
            item.precio_unitario * item.cantidad
            for item in pedido.items.all()
        )
        Pedido.objects.filter(pk=pedido.pk).update(total=nuevo_total)

    Orden.objects.filter(
        pedido__items__producto=instance,
        estado='abierta'
    ).distinct().update(subtotal=instance.precio)