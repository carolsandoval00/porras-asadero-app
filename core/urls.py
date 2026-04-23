
from django.contrib import admin
from django.urls import path, include
from core.views import inicio, inicio_admin
from usuarios.views import inicio_usuarios

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('reservas/', include('reservas.urls')),
    path('pedidos/', include('pedidos.urls')),
    # Cambia esto para que sea una ruta independiente
    path('pagos/', include('pago.urls')), 
    
    path('', inicio, name='inicio'),
    path('panel/', inicio_usuarios, name='inicio_admin'),
]
