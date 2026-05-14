from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


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
        ('pendiente',  'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('listo',      'Listo'),
        ('cancelado',  'Cancelado'),
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
        if not self.numero_orden:
            self.numero_orden = f"ORD-{self.pedido.pk:05d}"
        self.total = self.subtotal + self.impuesto
        super().save(*args, **kwargs)


@receiver(post_save, sender=Producto)
def actualizar_ordenes_al_cambiar_producto(sender, instance, **kwargs):
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