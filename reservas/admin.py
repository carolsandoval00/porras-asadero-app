from django.contrib import admin

from .models import *
# Register your models here.
admin.site.register(Mesa)
admin.site.register(Reserva)
admin.site.register(DetalleReserva)
