"""Asistente virtual del panel administrativo (PIA para Porras Asadero).

Adaptado de un widget original hecho para otro proyecto (Skyed, backend en
PHP). Aquí reescribimos la lógica en Django/Python y el "cerebro" del
asistente para que hable de Porras Asadero: mesas, reservas y pedidos,
usando datos reales de la base de datos (solo conteos/resúmenes, nunca
datos personales de clientes).
"""
import json
import os
import urllib.request
import urllib.error
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from reservas.models import Mesa, Reserva
from pedidos.models import Pedido

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
GEMINI_URL = (
    f'https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent'
)
MAX_TOKENS = 1000
MAX_HISTORIAL = 10  # solo los últimos N turnos, para no gastar tokens de más


def _construir_contexto_admin():
    """Arma un resumen en texto plano del estado actual del restaurante.

    Solo se envían conteos y estados agregados (nunca nombres de clientes
    ni datos personales), para que el asistente pueda responder preguntas
    del panel sin exponer información sensible a la API externa.
    """
    hoy = date.today()

    mesas_qs = Mesa.objects.all()
    total_mesas = mesas_qs.count()
    libres = mesas_qs.filter(estado='LIBRE').count()
    ocupadas = mesas_qs.filter(estado='OCUPADA').count()
    reservadas_mesa = mesas_qs.filter(estado='RESERVADA').count()

    reservas_hoy = Reserva.objects.filter(fecha_reserva=hoy)
    reservas_hoy_count = reservas_hoy.count()
    reservas_confirmadas = reservas_hoy.filter(estado='CONFIRMADA').count()
    reservas_pendientes = reservas_hoy.filter(estado='PENDIENTE').count()

    pedidos_preparacion = Pedido.objects.filter(estado='PREPARACION').count()
    pedidos_servidos_hoy = Pedido.objects.filter(
        estado='SERVIDO', fecha_creacion__date=hoy
    ).count()
    pedidos_pagados_hoy = Pedido.objects.filter(
        estado='PAGADO', fecha_creacion__date=hoy
    ).count()

    return (
        f"Fecha de hoy: {hoy.strftime('%A %d de %B de %Y')}.\n"
        f"Mesas: {total_mesas} en total — {libres} libres, {ocupadas} ocupadas, "
        f"{reservadas_mesa} reservadas.\n"
        f"Reservas de hoy: {reservas_hoy_count} en total "
        f"({reservas_confirmadas} confirmadas, {reservas_pendientes} pendientes).\n"
        f"Pedidos en preparación ahora mismo: {pedidos_preparacion}.\n"
        f"Pedidos servidos hoy: {pedidos_servidos_hoy}. Pedidos pagados hoy: {pedidos_pagados_hoy}."
    )


def _construir_system_prompt(nombre_usuario):
    fecha_hoy = datetime.now().strftime('%A, %d de %B de %Y')
    contexto_datos = _construir_contexto_admin()

    return f"""Te llamas PIA (Porras IA), el Asistente Virtual del panel administrativo de
Porras Asadero, un restaurante de comida a la brasa ubicado en Sogamoso, Boyacá,
Colombia. Hablas con {nombre_usuario or 'un miembro del personal'}, que está
usando el sistema de gestión para Porras Asadero (módulos de Reservas, Pedidos
y Carta, y Gestión de Pagos).

Hoy es: {fecha_hoy} (hora de Colombia).

Estado actual del restaurante (datos reales, agregados, sin información
personal de clientes):
{contexto_datos}

Tu trabajo:
- Responder preguntas del personal sobre el estado del restaurante usando los
  datos de arriba (mesas disponibles, reservas de hoy, pedidos en curso, etc.).
- Si te preguntan algo que no está en los datos de arriba (ej. el nombre de un
  cliente específico, el detalle de una reserva puntual, cifras de otro día),
  dilo con honestidad y sugiere en qué sección del panel puede consultarlo
  (Reservas y Mesas, Pedidos y Carta, o Gestión de Pagos).
- También puedes ayudar con preguntas generales rápidas (una operación
  matemática, una duda de redacción, etc.) con toda naturalidad.
- Responde siempre en español, de forma cálida, cercana y breve (2-4 frases
  en general). Evita párrafos largos: esto es un chat de panel administrativo,
  no un informe.
- Formato: puedes usar **negrita** para resaltar y listas con "- " cuando
  ayuden a ordenar varias cosas. No uses LaTeX ni notación matemática con
  símbolos raros — escribe todo como texto normal.
- No inventes datos que no tengas (números de mesa, nombres, cifras de
  ventas). Si no lo sabes, dilo.
"""


def _llamar_gemini(system_prompt, historial, mensaje_usuario):
    contents = []
    for turno in historial[-MAX_HISTORIAL:]:
        role = turno.get('role')
        content = turno.get('content')
        if not role or not content:
            continue
        contents.append({
            'role': 'model' if role == 'assistant' else 'user',
            'parts': [{'text': str(content)}],
        })

    contents.append({'role': 'user', 'parts': [{'text': mensaje_usuario}]})

    payload = {
        'contents': contents,
        'systemInstruction': {'parts': [{'text': system_prompt}]},
        'generationConfig': {'maxOutputTokens': MAX_TOKENS},
    }

    req = urllib.request.Request(
        GEMINI_URL,
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'x-goog-api-key': GEMINI_API_KEY,
        },
        method='POST',
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))

    partes = data.get('candidates', [{}])[0].get('content', {}).get('parts', [])
    texto = ''.join(p.get('text', '') for p in partes)
    return texto or 'No obtuve una respuesta clara, ¿puedes reformular tu pregunta?'


@login_required
@require_POST
def chat_ia(request):
    """Endpoint del panel admin: recibe un mensaje y responde con Gemini."""
    if not GEMINI_API_KEY:
        return JsonResponse(
            {'error': 'Falta configurar GEMINI_API_KEY en el archivo .env del servidor.'},
            status=500,
        )

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'error': 'Cuerpo de la petición inválido.'}, status=400)

    mensaje = (body.get('message') or '').strip()
    if not mensaje:
        return JsonResponse({'error': 'Falta el mensaje del usuario.'}, status=400)
    mensaje = mensaje[:1000]

    historial = body.get('history') or []
    if not isinstance(historial, list):
        historial = []

    nombre_usuario = getattr(request.user, 'first_name', '') or request.user.get_username()
    system_prompt = _construir_system_prompt(nombre_usuario)

    try:
        respuesta = _llamar_gemini(system_prompt, historial, mensaje)
    except urllib.error.HTTPError as e:
        detalle = e.read().decode('utf-8', errors='replace')
        return JsonResponse(
            {'error': 'La IA no respondió correctamente.', 'detail': detalle}, status=502
        )
    except urllib.error.URLError as e:
        return JsonResponse(
            {'error': 'No se pudo conectar con el asistente.', 'detail': str(e.reason)},
            status=502,
        )

    return JsonResponse({'reply': respuesta})