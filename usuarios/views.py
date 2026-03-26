from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from .forms import CustomPasswordResetForm
from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import PersonalForm
from .models import Personal
class CustomPasswordResetView(PasswordResetView):
    template_name = 'usuarios/recuperar.html'
    form_class = CustomPasswordResetForm
    success_url = reverse_lazy('recuperar_enviado')


def registrar_personal(request):
    if request.method == 'POST':
        form = PersonalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "¡Personal registrado correctamente!")
            return redirect('lista_personal')
    else:
        form = PersonalForm()
    return render(request, 'usuarios/registrar_personal.html', {'form': form})

def lista_personal(request):
    personal_list = Personal.objects.all()
    return render(request, 'usuarios/lista_personal.html', {'personal_list': personal_list})
