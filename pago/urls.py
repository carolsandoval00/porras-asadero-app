from django.urls import path
from . import views

app_name = 'pago'

urlpatterns = [
    path('', views.pago_dashboard, name='dashboard'),
    path('<int:pk>/editar/', views.pago_editar, name='editar'),
    path('<int:pk>/eliminar/', views.pago_eliminar, name='eliminar'),
    path('caja/<int:pk>/', views.caja_detalle, name='caja_detalle'),
    path('pagos/reporte/pdf/', views.pagos_exportar_pdf, name='pagos_pdf'),
    path('pagos/reporte/excel/', views.pagos_exportar_excel, name='pagos_excel'),
    path('pagos/reporte/imprimir/', views.pagos_imprimir, name='pagos_imprimir'),
]