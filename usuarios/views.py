from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from .forms import CustomPasswordResetForm

class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuarios/recuperar.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('recuperar_enviado')