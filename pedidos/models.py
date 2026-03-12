from django.db import models

class Producto(models.Model):
    codigo_producto = models.AutoField(primary_key=True)
    nombre_producto = models.CharField(max_length=100)
    categoria = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=200)
    estado = models.CharField(max_length=50)

    def __str__(self):
        return self.nombre_producto


class Pedido(models.Model):
    numero_pedido = models.AutoField(primary_key=True)
    fecha = models.DateField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=50)

    def __str__(self):
        return f"Pedido {self.numero_pedido}"


class Orden(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.IntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Orden {self.pedido}"
