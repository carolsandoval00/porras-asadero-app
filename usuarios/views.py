from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import PersonalForm
from .models import Personal

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