from django.db import models


class Caja(models.Model):
    codigo = models.AutoField(primary_key=True)
    fecha_apertura = models.DateTimeField()
    fecha_cierre = models.DateTimeField()
    numero_caja = models.IntegerField()
    cajero_responsable = models.CharField(max_length=100)
    saldo_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    saldo_final = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Caja {self.numero_caja}"


class Pago(models.Model):
    numero_pago = models.AutoField(primary_key=True)
    fecha_pago = models.DateField()
    metodo_pago = models.CharField(max_length=50)
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Pago {self.numero_pago}"
