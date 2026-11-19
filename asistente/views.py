"""Asistente virtual del panel administrativo (PIA para Porras Asadero)."""
import json
import os
from datetime import date, datetime

import httpx
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from reservas.models import Mesa, Reserva
from pedidos.models import Pedido

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
GEMINI_MODEL = os.environ.get('GEMINI_MODEL', 'gemini-3.5-flash-lite')
GEMINI_MODEL_RESPALDO = os.environ.get(
    'GEMINI_MODEL_RESPALDO',
    'gemini-3.5-flash',
)
GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent'
MAX_TOKENS = 2000
TIMEOUT_SEGUNDOS = 60
MAX_HISTORIAL = 10


class GeminiError(Exception):
    """Error devuelto por la API gratuita de Gemini."""


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

=== TONO (regla estricta, sin excepciones) ===
- Profesional, amable, claro, natural y paciente.
- Prohibido: sarcasmo, burlas, ironía, chistes ofensivos, comentarios
  pasivo-agresivos, groserías, tono despectivo o condescendiente.
- Nunca trates al usuario como si hubiera cometido un error o hecho una
  pregunta tonta. No asumas intenciones negativas: si un mensaje es
  ambiguo, pide una aclaración de forma respetuosa en vez de interpretarlo
  de la peor manera.
- Evita la formalidad exagerada (nada de "estimado usuario" ni lenguaje
  rebuscado) y evita también el exceso de emojis. Sé natural y humano,
  como un compañero de trabajo capacitado, no como un chatbot genérico.
- Respuestas breves (2-4 frases en general). Esto es un chat de panel
  administrativo, no un informe.

=== ENFOQUE EN EL SISTEMA (regla estricta) ===
- Tu función es ayudar con el sistema de Porras Asadero: Reservas, Mesas,
  Pedidos, Carta y Gestión de Pagos.
- Responde siempre basándote en los datos reales de arriba y en los
  módulos que realmente existen en el sistema. NUNCA inventes
  funcionalidades, módulos, datos, cifras o nombres que no estén
  presentes en este prompt o en el mensaje del usuario.
- Si te preguntan algo que no está en los datos de arriba (ej. el nombre
  de un cliente específico, el detalle de una reserva puntual, cifras de
  otro día), dilo con honestidad — di claramente que no tienes esa
  información — y sugiere en qué sección del panel puede consultarlo
  (Reservas y Mesas, Pedidos y Carta, o Gestión de Pagos). No inventes una
  respuesta para rellenar el vacío.
- Si te piden explicar cómo hacer algo en el sistema (crear una reserva,
  cambiar el estado de una mesa, generar un reporte, etc.), explica los
  pasos de forma clara y concreta, usando los módulos y nombres reales
  del sistema.

=== PREGUNTAS FUERA DE CONTEXTO (regla estricta) ===
- Si el usuario pregunta algo que no tiene relación con Porras Asadero ni
  con el sistema (temas generales, cultura, matemáticas sueltas, charla
  casual, etc.), respóndele de forma breve y educada indicando que tu
  función principal es ayudar con el sistema de Porras Asadero, y
  ofrécele ayuda con algo relacionado al panel.
- No desarrolles el tema fuera de contexto ni inicies una conversación
  nueva sobre él. Un ejemplo de tono correcto: "Ese tema no está
  relacionado con el sistema, así que no puedo ayudarte con eso aquí.
  ¿Te ayudo con algo de Reservas, Pedidos o Pagos?"

=== FORMATO ===
- Responde siempre en español.
- Puedes usar **negrita** para resaltar y listas con "- " cuando ayuden a
  ordenar varias cosas.
- No uses LaTeX ni notación matemática con símbolos raros — escribe todo
  como texto normal.
"""


def _llamar_gemini(system_prompt, historial, mensaje_usuario):
    contents = []

    for turno in historial[-MAX_HISTORIAL:]:
        if not isinstance(turno, dict):
            continue
        role = turno.get('role')
        content = turno.get('content')
        if not role or not content:
            continue
        contents.append({
            'role': 'model' if role == 'assistant' else 'user',
            'parts': [{'text': str(content)}],
        })

    while contents and contents[0]['role'] == 'model':
        contents.pop(0)

    contents.append({'role': 'user', 'parts': [{'text': mensaje_usuario}]})

    modelos = [GEMINI_MODEL]
    modelos.extend(m.strip() for m in GEMINI_MODEL_RESPALDO.split(',') if m.strip())

    respuesta = None
    ultimo_error = None

    for modelo in modelos:
        try:
            respuesta = httpx.post(
                GEMINI_URL.format(modelo=modelo),
                headers={'x-goog-api-key': GEMINI_API_KEY},
                json={
                    'system_instruction': {'parts': [{'text': system_prompt}]},
                    'contents': contents,
                    'generationConfig': {'maxOutputTokens': MAX_TOKENS},
                },
                timeout=TIMEOUT_SEGUNDOS,
            )
        except httpx.TimeoutException as error:
            ultimo_error = error
            continue

        if respuesta.status_code == 200:
            break

        ultimo_error = GeminiError(f'{respuesta.status_code}: {respuesta.text[:300]}')
        if respuesta.status_code not in (429, 500, 503):
            break

    if respuesta is None:
        raise ultimo_error or GeminiError('No hubo respuesta de Gemini.')

    if respuesta.status_code != 200:
        raise ultimo_error or GeminiError(f'{respuesta.status_code}: {respuesta.text[:300]}')

    try:
        partes = respuesta.json()['candidates'][0]['content']['parts']
        texto = ''.join(parte.get('text', '') for parte in partes)
    except (KeyError, IndexError, TypeError, ValueError):
        texto = ''

    return texto or 'No obtuve una respuesta clara, ¿puedes reformular tu pregunta?'


def _respuesta_sin_ia():
    """Respuesta de emergencia: el estado del restaurante leído directo de la base de datos."""
    return (
        "Ahora mismo no puedo conectarme con la IA, pero este es el estado actual "
        "del restaurante según el sistema:\n\n"
        + _construir_contexto_admin()
        + "\n\nIntenta de nuevo en un momento si necesitas otra cosa."
    )


@login_required
@require_POST
def chat_ia(request):
    """Endpoint del panel admin: recibe un mensaje y responde con Gemini gratuito."""
    if not GEMINI_API_KEY or not GEMINI_MODEL:
        return JsonResponse(
            {'error': 'Falta configurar GEMINI_API_KEY y GEMINI_MODEL en el archivo .env del servidor.'},
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
    except GeminiError as e:
        print("PIA error:", e)
        return JsonResponse({'reply': _respuesta_sin_ia()})
    except httpx.TimeoutException:
        print("PIA error: tiempo de espera agotado en todos los intentos")
        return JsonResponse({'reply': _respuesta_sin_ia()})
    except httpx.HTTPError as e:
        print("PIA error de red:", repr(e))
        return JsonResponse({'reply': _respuesta_sin_ia()})

    return JsonResponse({'reply': respuesta})