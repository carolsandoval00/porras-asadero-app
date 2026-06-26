from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre      = models.CharField(max_length=200)
    categoria   = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='productos', verbose_name='Categoría')
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
    TIPO_PEDIDO_CHOICES = [
        ('LOCAL', 'Local'),
        ('LLEVAR', 'Para Llevar'),
        ('DOMICILIO', 'Domicilio'),
    ]
    ESTADO_CHOICES = [
        ('PREPARACION', 'En Preparación'),
        ('SERVIDO', 'Servido'),
        ('PAGADO', 'Pagado'),
        ('CANCELADO', 'Cancelado'),
    ]
    id                  = models.AutoField(primary_key=True)
    cliente             = models.ForeignKey('usuarios.Cliente', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos', verbose_name='Cliente')
    mesero              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='pedidos_atendidos', verbose_name='Mesero')
    mesa                = models.ForeignKey('reservas.Mesa', on_delete=models.SET_NULL, null=True, blank=True, related_name='pedidos', verbose_name='Mesa')
    tipo_pedido         = models.CharField(max_length=20, choices=TIPO_PEDIDO_CHOICES, default='LOCAL', verbose_name='Tipo de Pedido')
    estado              = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='PREPARACION', verbose_name='Estado')
    descripcion         = models.TextField(blank=True, null=True, verbose_name="Descripción")
    subtotal            = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    impuestos           = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total               = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_creacion      = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'mod_pedido'
        ordering = ['-fecha_creacion']
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'

    @property
    def numero_orden(self):
        return f"ORD-{self.id:05d}"

    @property
    def numero_pedido(self):
        return f"PED-{self.id:05d}"

    @property
    def impuesto(self):
        return self.impuestos

    @property
    def notas(self):
        return self.descripcion

    def __str__(self):
        cliente_str = self.cliente.nombre_completo if self.cliente else "Cliente de Paso"
        return f'Pedido #{self.pk} - {cliente_str}'


class PedidoItem(models.Model):
    pedido          = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='items')
    producto        = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='items')
    cantidad        = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    notas           = models.CharField(max_length=255, blank=True, null=True, verbose_name="Notas")

    class Meta:
        db_table = 'mod_pedido_item'
        verbose_name = 'Item de Pedido'
        verbose_name_plural = 'Items de Pedido'

    def __str__(self):
        return f'{self.cantidad}x {self.producto.nombre}'

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad


@receiver(post_save, sender=Producto)
def actualizar_pedidos_al_cambiar_producto(sender, instance, **kwargs):
    pedidos_con_producto = Pedido.objects.filter(
        items__producto=instance,
        estado='PREPARACION'
    ).distinct()

    for pedido in pedidos_con_producto:
        pedido.items.filter(producto=instance).update(precio_unitario=instance.precio)
        nuevo_total = sum(
            item.precio_unitario * item.cantidad
            for item in pedido.items.all()
        )
        Pedido.objects.filter(pk=pedido.pk).update(total=nuevo_total, subtotal=nuevo_total)