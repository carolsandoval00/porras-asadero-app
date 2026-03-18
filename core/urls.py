
from django.contrib import admin
from django.urls import include,path

from core.views import inicio

urlpatterns = [
    path('admin/', admin.site.urls),
    path('reservas/', include ('reservas.urls')), 
    path('usuarios/', include ('usuarios.urls')), 
    path('pedidos/', include ('pedidos.urls')), 
    path('pago/', include ('pago.urls')), 
    path('',  inicio, name='inicio'), 
]


