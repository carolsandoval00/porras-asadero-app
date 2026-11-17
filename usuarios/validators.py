"""
Validaciones compartidas para crear / editar usuarios (Porras Asadero).

Se usan desde usuarios/forms.py. Las mismas reglas están replicadas en el
navegador en static/js/validaciones_usuario.js; si cambias una regla aquí,
cámbiala también allá para que el aviso salga antes de enviar el formulario.
"""
import re
import unicodedata

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

# ═════════════════════════════════════════════════════════════
#  AJUSTES (cámbialos aquí si cambian las reglas del negocio)
# ═════════════════════════════════════════════════════════════
PASSWORD_MIN = 6
PASSWORD_MAX = 8

# Formato de documentos en Colombia: (expresión regular, mensaje)
FORMATOS_DOCUMENTO = {
    'CC': (r'[1-9]\d{5,9}',
           'La cédula debe tener entre 6 y 10 dígitos, sin letras y sin empezar en 0.'),
    'TI': (r'[1-9]\d{9,10}',
           'La tarjeta de identidad debe tener 10 u 11 dígitos, sin empezar en 0.'),
    'CE': (r'[1-9]\d{5,6}',
           'La cédula de extranjería debe tener 6 o 7 dígitos, sin empezar en 0.'),
    'PP': (r'(?=.*\d)[A-Z0-9]{6,9}',
           'El pasaporte debe tener entre 6 y 9 letras y números, con al menos un número.'),
}

MSG_DOC_CONSECUTIVOS = (
    'El documento tiene demasiados números consecutivos o repetidos (ej: 1234567). Escribe uno real.'
)

# Palabras que pueden ir en minúscula dentro de un nombre ("María de los Ángeles")
PARTICULAS = {'de', 'del', 'la', 'las', 'los', 'y', 'e'}

# Filas del teclado: sirven para detectar textos escritos al azar ("asdfgh")
FILAS_TECLADO = ['qwertyuiop', 'asdfghjkl', 'zxcvbnm']

# Pares de consonantes que SÍ existen en nombres y apellidos (hispanos y extranjeros comunes).
# Cualquier otro par seguido (sd, jk, fg, kj, hj…) se considera texto escrito al azar.
PARES_CONSONANTES = set((
    'bb bl br bs bd cc ch ck cl cq cr cs ct dd dg dj dm dr ds dv dw ff fl fr gd gg gh gl gn gr gs '
    'hl hm hn hr jh kh kl kn kr ks lb lc ld lf lg lj lk ll lm ln lp lq ls lt lv lz mb mc mm mn mp ms '
    'nc nd nf ng nh nj nk nl nm nn nq nr ns nt nv nz pl pr ps pt ph pp '
    'rb rc rd rf rg rh rj rk rl rm rn rp rq rr rs rt rv rw rz sb sc sf sh sk sl sm sp sq ss st sv sw sz '
    'tl tr th tt ts tz wh xc xp xt zc zh zm zz'
).split())

# Proporción de letras seguidas en teclas vecinas a partir de la cual se considera tecleo al azar
RATIO_VECINOS = 0.75

# Palabras de relleno que no son nombres reales
NOMBRES_FALSOS = {
    'test', 'tester', 'prueba', 'pruebas', 'nombre', 'nombres', 'apellido', 'apellidos', 'usuario',
    'admin', 'administrador', 'fulano', 'fulana', 'mengano', 'mengana', 'zutano', 'perengano',
    'lorem', 'ipsum', 'ejemplo', 'ninguno', 'ninguna', 'nada', 'nadie', 'abc', 'abcd', 'xxx',
    'asdf', 'qwerty', 'null', 'none', 'undefined', 'anonimo', 'sinnombre', 'sapo', 'hola',
}

# Nombres reales poco comunes que las reglas genéricas rechazarían por error
EXCEPCIONES = set('''
abner aguayo ariadna asdrubal aznar barba barbara blanch blazquez capdevila casas cases
cisneros concepcion dafne derek duilio dwight eder edna edwar edward efren esneider feliu
ferrer franch fredes fredy isaza israel izquierdo julio lilia lillo neftali peres plaza polo
sastre schmidt schwartz sergio sessa sigfrido sisneros sneider teresa vazquez velazquez
vladimir washington wladimir yasna
'''.split())

DOMINIOS_DESECHABLES = {
    'mailinator.com', 'tempmail.com', 'temp-mail.org', '10minutemail.com',
    'guerrillamail.com', 'yopmail.com', 'trashmail.com', 'throwawaymail.com',
    'getnada.com', 'sharklasers.com', 'dispostable.com', 'maildrop.cc',
    'fakeinbox.com', 'mintemail.com', 'tempinbox.com', 'mohmal.com',
}

# Errores de tipeo frecuentes → dominio correcto
DOMINIOS_TYPO = {
    'gmial.com': 'gmail.com', 'gamil.com': 'gmail.com', 'gmai.com': 'gmail.com',
    'gmil.com': 'gmail.com', 'gmail.co': 'gmail.com', 'gmail.con': 'gmail.com',
    'gmail.comm': 'gmail.com', 'gnail.com': 'gmail.com',
    'hotmial.com': 'hotmail.com', 'hotmal.com': 'hotmail.com',
    'hotmail.con': 'hotmail.com', 'hotmai.com': 'hotmail.com',
    'outlok.com': 'outlook.com', 'outloo.com': 'outlook.com', 'outlook.con': 'outlook.com',
    'yaho.com': 'yahoo.com', 'yahooo.com': 'yahoo.com', 'yahoo.con': 'yahoo.com',
}

CONTRASENAS_COMUNES = {
    'password', 'contrasena', 'contraseña', 'qwerty', 'admin', 'porras',
    'asadero', 'abc123', 'letmein', 'welcome', 'colombia',
}


# ═════════════════════════════════════════════════════════════
#  Utilidades
# ═════════════════════════════════════════════════════════════
def _sin_acentos(texto):
    return ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )


def _en_teclado(palabra):
    """True si la palabra es (casi) una tira de teclas contiguas: asdf, qwerty, zxcv…"""
    n = len(palabra)
    if n < 4:
        return False
    for fila in FILAS_TECLADO:
        for tira in (fila, fila[::-1]):
            if n <= 4 and palabra in tira:
                return True
            if n > 4 and any(palabra[i:i + 5] in tira for i in range(n - 4)):
                return True
    return False


def _ratio_vecinos(w):
    """Proporción de letras seguidas que están en teclas vecinas del teclado (qwerty)."""
    pos = {c: (r, i) for r, fila in enumerate(FILAS_TECLADO) for i, c in enumerate(fila)}
    pares = list(zip(w, w[1:]))
    if not pares:
        return 0.0
    vecinas = 0
    for a, b in pares:
        if a in pos and b in pos and a != b:
            (r1, i1), (r2, i2) = pos[a], pos[b]
            if abs(r1 - r2) <= 1 and abs(i1 - i2) <= 1:
                vecinas += 1
    return vecinas / len(pares)


def _parece_palabra_real(palabra, minimo_vocales=0.2, estricto=False):
    """
    Heurística para descartar texto escrito al azar (gfdgsfddsv, asdasd, jajaja, lolol…).
    estricto=True (nombres y apellidos) además exige que cada par de consonantes
    seguidas exista en español; en correos no se usa porque "jperez" es normal.
    """
    w = _sin_acentos(palabra.lower())
    if estricto and w in EXCEPCIONES:
        return True
    if len(w) < 2:
        return False
    if not re.search(r'[aeiouy]', w):                 # sin vocales
        return False
    if re.search(r'(.)\1\1', w):                       # tres letras iguales seguidas
        return False
    if re.search(r'[^aeiouy]{5,}', w):                 # 5 consonantes seguidas
        return False
    if re.search(r'[aeiouy]{4,}', w):                  # 4 vocales seguidas (aeiou)
        return False
    if re.search(r'(..)\1\1', w):                      # patrón repetido: ababab
        return False
    if re.search(r'(.{3})\1', w):                       # sílaba de 3 repetida: asdasd
        return False
    for periodo in (2, 3):                             # palabra periódica: lolol, jajaj
        if len(w) >= 5 and w == (w[:periodo] * len(w))[:len(w)]:
            return False
    if len(w) >= 5:
        vocales = len(re.findall(r'[aeiouy]', w))
        if vocales / len(w) < minimo_vocales:
            return False
    if _en_teclado(w):
        return False
    if estricto:
        if len(w) >= 4 and _ratio_vecinos(w) >= RATIO_VECINOS:     # tecleo sobre teclas vecinas: likik, uioliop
            return False
        for a, b in zip(w, w[1:]):
            if a not in 'aeiouy' and b not in 'aeiouy' and (a + b) not in PARES_CONSONANTES:
                return False
    return True


def _capitalizar(texto):
    """'juan CARLOS de la cruz' -> 'Juan Carlos de la Cruz' (respeta mayúsculas mixtas: McDonald)."""
    partes = re.split(r"([ \-'])", texto)
    resultado = []
    primera = True
    for parte in partes:
        if parte in (' ', '-', "'") or not parte:
            resultado.append(parte)
            continue
        if not primera and parte.lower() in PARTICULAS:
            resultado.append(parte.lower())
        elif parte.islower() or parte.isupper():
            resultado.append(parte.capitalize())
        else:
            resultado.append(parte)
        primera = False
    return ''.join(resultado)


# ═════════════════════════════════════════════════════════════
#  1. Nombres y apellidos
# ═════════════════════════════════════════════════════════════
def validar_nombre(value, campo='nombre', max_length=60):
    if not value or not str(value).strip():
        raise ValidationError(f'Debes escribir el {campo}.')
    texto = re.sub(r'\s+', ' ', str(value).strip())

    if len(texto) > max_length:
        raise ValidationError(f'El {campo} no puede superar {max_length} caracteres.')
    if not re.fullmatch(r"[A-Za-záéíóúÁÉÍÓÚüÜñÑ]+(?:[ \-'][A-Za-záéíóúÁÉÍÓÚüÜñÑ]+)*", texto):
        raise ValidationError(f'El {campo} solo puede tener letras y espacios (sin números ni símbolos).')

    palabras = [p.replace("'", '') for p in re.split(r'[ \-]', texto) if p]
    reales = [p for p in palabras if p and p.lower() not in PARTICULAS]
    ejemplo = 'Juan Carlos' if campo == 'nombre' else 'Pérez López'
    if any(_sin_acentos(p.lower()) in NOMBRES_FALSOS for p in reales):
        raise ValidationError(f'Escribe tu {campo} real, no una palabra de relleno (ej: {ejemplo}).')
    if not reales:
        raise ValidationError(f'Escribe un {campo} real.')
    for palabra in reales:
        if not _parece_palabra_real(palabra, estricto=True):
            raise ValidationError(
                f'Escribe un {campo} real, sin letras al azar (ej: {ejemplo}).'
            )
    return _capitalizar(texto)


# ═════════════════════════════════════════════════════════════
#  2. Número de documento (formato Colombia)
# ═════════════════════════════════════════════════════════════
def _hay_secuencia(valor, largo=5):
    """True si hay `largo` o más dígitos seguidos ascendentes o descendentes (12345, 98765, 67890)."""
    if len(valor) < largo:
        return False
    for i in range(len(valor) - largo + 1):
        ventana = valor[i:i + largo]
        if not ventana.isdigit():
            continue
        difs = {(int(ventana[j + 1]) - int(ventana[j])) % 10 for j in range(largo - 1)}
        if difs == {1} or difs == {9}:
            return True
    return False


def validar_documento(tipo, numero):
    """
    Valida tipo + número. Devuelve el número limpio, o None si ambos vienen vacíos
    (el documento es opcional, pero si se llena uno hay que llenar el otro).
    """
    tipo = (tipo or '').strip().upper()
    numero = re.sub(r'[\s.\-]', '', str(numero or '')).upper()

    if not tipo and not numero:
        return None
    if not tipo:
        raise ValidationError('Debes elegir el tipo de documento.')
    if not numero:
        raise ValidationError('Debes escribir el número de documento.')
    if tipo not in FORMATOS_DOCUMENTO:
        raise ValidationError('El tipo de documento no es válido.')

    patron, mensaje = FORMATOS_DOCUMENTO[tipo]
    if not re.fullmatch(patron, numero):
        raise ValidationError(mensaje)

    # Demasiados números consecutivos o repetidos
    if (re.search(r'(.)\1{3,}', numero)                 # 1111, 0000…
            or _hay_secuencia(numero)                   # 12345, 98765…
            or re.fullmatch(r'(.{1,4})\1+', numero)     # 12121212, 12341234
            or re.fullmatch(r'(?:(.)\1)+', numero)      # 11223344, 1122334455
            or len(set(numero)) < (4 if len(numero) >= 8 else 3)):
        raise ValidationError(MSG_DOC_CONSECUTIVOS)
    return numero


# ═════════════════════════════════════════════════════════════
#  Teléfono (celular colombiano: 10 dígitos que empiezan por 3)
# ═════════════════════════════════════════════════════════════
def validar_telefono(value):
    """Devuelve el número, o None si viene vacío (el teléfono es opcional)."""
    numero = str(value or '').strip()
    if not numero:
        return None
    if not numero.isdigit():
        raise ValidationError('El teléfono solo debe contener números.')
    if not numero.startswith('3'):
        raise ValidationError('El teléfono debe empezar por 3 (celular), ej: 3001234567.')
    if len(numero) != 10:
        raise ValidationError('El teléfono debe tener 10 dígitos, ej: 3001234567.')
    return numero


# ═════════════════════════════════════════════════════════════
#  3. Correo electrónico
# ═════════════════════════════════════════════════════════════
def _dominio_existe(dominio):
    """Consulta MX/A si hay dnspython instalado. Si no hay internet o librería, no bloquea."""
    try:
        import dns.resolver
    except ImportError:
        return True
    try:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 3
        try:
            resolver.resolve(dominio, 'MX')
        except dns.resolver.NoAnswer:
            resolver.resolve(dominio, 'A')
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
        return False
    except Exception:
        return True   # sin conexión / timeout: no castigar al usuario


def validar_correo(value):
    email = str(value or '').strip().lower()
    if not email:
        raise ValidationError('Debes escribir el correo electrónico.')

    msg_formato = 'Escribe un correo real (ej: nombre@gmail.com).'
    try:
        validate_email(email)
    except ValidationError:
        raise ValidationError(msg_formato)

    local, dominio = email.rsplit('@', 1)
    if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?\.)+[a-z]{2,}', dominio):
        raise ValidationError(msg_formato)
    if len(local) < 3:
        raise ValidationError(msg_formato)

    if dominio in DOMINIOS_TYPO:
        raise ValidationError(f'¿Quisiste escribir @{DOMINIOS_TYPO[dominio]}? Revisa el dominio del correo.')
    if dominio in DOMINIOS_DESECHABLES:
        raise ValidationError('No se permiten correos temporales o desechables. Usa tu correo real.')

    # Reglas propias de Gmail: 6-30 caracteres, solo letras, números y puntos
    if dominio in ('gmail.com', 'googlemail.com'):
        base = local.split('+')[0]
        if (not 6 <= len(base) <= 30 or not re.fullmatch(r'[a-z0-9.]+', base)
                or base.startswith('.') or base.endswith('.') or '..' in base):
            raise ValidationError('Ese correo de Gmail no es válido. Escribe tu correo real.')

    # La parte antes de la @ no puede ser texto al azar
    if re.fullmatch(r'[\d._+\-]+', local):
        raise ValidationError(msg_formato)
    for bloque in re.findall(r'[a-z]+', _sin_acentos(local)):
        if len(bloque) >= 4 and not _parece_palabra_real(bloque, minimo_vocales=0.2):
            raise ValidationError(
                'Ese correo parece escrito al azar. Escribe un correo real (ej: nombre@gmail.com).'
            )

    if not _dominio_existe(dominio):
        raise ValidationError(f'El dominio @{dominio} no existe. Revisa el correo.')
    return email


# ═════════════════════════════════════════════════════════════
#  4. Contraseña (6 a 8 caracteres)
# ═════════════════════════════════════════════════════════════
def _secuencia_clave(pw, largo=4):
    p = _sin_acentos(pw.lower())
    for i in range(len(p) - largo + 1):
        v = p[i:i + largo]
        if not v.isalnum():
            continue
        if all(ord(v[j + 1]) - ord(v[j]) == 1 for j in range(largo - 1)):
            return True
        if all(ord(v[j]) - ord(v[j + 1]) == 1 for j in range(largo - 1)):
            return True
    return False


def validar_password(pw, usuario=''):
    """Devuelve la contraseña si es válida; si no, lanza ValidationError con TODOS los problemas."""
    pw = pw or ''
    errores = []

    if not pw:
        raise ValidationError('Debes escribir la contraseña.')
    requisitos = []
    if not PASSWORD_MIN <= len(pw) <= PASSWORD_MAX:
        requisitos.append(f'tener entre {PASSWORD_MIN} y {PASSWORD_MAX} caracteres')
    if ' ' in pw:
        requisitos.append('no tener espacios')

    faltan = []
    if not re.search(r'[A-Z]', pw):
        faltan.append('una mayúscula')
    if not re.search(r'[a-z]', pw):
        faltan.append('una minúscula')
    if not re.search(r'\d', pw):
        faltan.append('un número')
    if not any(not c.isalnum() and not c.isspace() for c in pw):
        faltan.append('un símbolo (@ # $ % & *)')
    if faltan:
        unidos = faltan[0] if len(faltan) == 1 else ', '.join(faltan[:-1]) + ' y ' + faltan[-1]
        requisitos.append('incluir ' + unidos)

    if requisitos:
        mensaje = 'La contraseña debe ' + requisitos[0]
        for extra in requisitos[1:]:
            mensaje += (' e ' if extra.startswith('incluir') else ' y ') + extra
        errores.append(mensaje + '.')

    if not errores:
        bloques = re.findall(r'[a-z]+', _sin_acentos(pw.lower()))
        if re.search(r'(.)\1\1', pw, re.I) or _secuencia_clave(pw) or any(_en_teclado(b) for b in bloques):
            errores.append('La contraseña es muy fácil de adivinar: evita repetidos o seguidos (aaa, 1234, abcd).')
        elif any(c in pw.lower() for c in CONTRASENAS_COMUNES):
            errores.append('Esa contraseña es muy común. Elige otra.')
        elif usuario and len(usuario) >= 3 and usuario.lower() in pw.lower():
            errores.append('La contraseña no puede contener tu nombre de usuario.')

    if errores:
        raise ValidationError(errores)
    return pw