from django.contrib import admin
from django.urls import path, include
from core.views import inicio, inicio_admin
from usuarios.views import inicio_usuarios
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('reservas/', include('reservas.urls')),
    path('pedidos/', include('pedidos.urls')),
    path('pagos/', include('pago.urls')), 
    
    path('', inicio, name='inicio'),
    
    # Aquí dejamos creadas ambas rutas para que ningún botón o redirección falle:
    path('panel/', inicio_usuarios, name='inicio_usuarios'),
    path('panel-admin/', inicio_admin, name='inicio_admin'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)