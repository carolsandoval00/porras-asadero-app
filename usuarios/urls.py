from django.urls import path
from .views import inicio_usuarios, registrar_personal

urlpatterns = [
    path('', inicio_usuarios),
    path('registrar/', registrar_personal),
]