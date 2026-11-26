from django.urls import path
from . import views


urlpatterns = [
    # AUTENTICACIÓN
    path('login/',       views.login_view,            name='login'),
    path('registro/',    views.registro_view,          name='registro'),
    path('logout/',      views.logout_view,            name='logout'),
    path('acceder/',     views.acceder_sistema,        name='acceder_sistema'),
    path('redireccion/', views.redireccion_post_login, name='redireccion'),
    path('inicio/',      views.inicio_usuarios,        name='inicio_usuarios'),

    # RECUPERACIÓN DE CONTRASEÑA
    path('recuperar/', views.recuperar_password, name='recuperar_password'),
    path('restablecer/<uidb64>/<token>/', views.restablecer_password, name='restablecer_password'),

    # GESTIÓN DE PERSONAL
    path('lista/',             views.lista_personal,    name='lista_personal'),
    path('perfil/',            views.panel_perfil,      name='panel_perfil'),
    path('inactivar/',         views.inactivar_usuario, name='inactivar_usuario'),
    path('eliminar/<int:id>/', views.eliminar_usuario,  name='eliminar_usuario'),
    path('sin-permisos/',      views.validar_permisos,  name='validar_permisos'),

    # ENDPOINTS JSON
    path('crear/',               views.crear_usuario,       name='crear_usuario'),
    path('editar/<int:id>/',     views.editar_usuario_json, name='editar_usuario_json'),
    path('actualizar/<int:pk>/', views.actualizar_usuario,  name='actualizar_usuarios'),

    # FOTO DE PERFIL
    path('foto/<int:pk>/', views.actualizar_foto, name='actualizar_foto'),
]