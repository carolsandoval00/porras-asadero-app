from django.urls import path
from . import views
from django.urls import path
from .views import DetalleUsuarioView

urlpatterns = [
    path('inactivar/', views.inactivar_usuario, name='inactivar_usuario'),
    path('', inicio_usuarios, name='inicio_usuarios'), 
    path('consultar/<int:pk>/', DetalleUsuarioView.as_view(), name='detalle_usuario'),

]