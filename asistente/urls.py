from django.urls import path
from . import views

app_name = 'asistente'

urlpatterns = [
    path('chat/', views.chat_ia, name='chat'),
]