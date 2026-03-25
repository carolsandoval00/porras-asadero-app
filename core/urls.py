from django.contrib import admin
from django.urls import path, include
from core.views import inicio

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('reservas/', include('reservas.urls')),
    path('pedidos/', include('pedidos.urls')),
    path('pago/', include('pago.urls')),

    path('', inicio, name='inicio'),
]