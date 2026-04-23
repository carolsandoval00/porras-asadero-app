from django.urls import path
from . import views

app_name = 'pago'

urlpatterns = [
    path('', views.pago_dashboard, name='dashboard'),
    path('<int:pk>/editar/', views.pago_editar, name='editar'),
    path('<int:pk>/eliminar/', views.pago_eliminar, name='eliminar'),
]