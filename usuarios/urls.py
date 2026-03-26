from django.urls import path
from .views import acceder_sistema

urlpatterns = [
    path('acceder/', acceder_sistema, name='acceder_sistema'),
]