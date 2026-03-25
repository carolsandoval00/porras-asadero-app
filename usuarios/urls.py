from django.urls import path
from .views import consultar_usuario

urlpatterns = [
    path('consultar/', consultar_usuario, name='consultar_usuario'),
]