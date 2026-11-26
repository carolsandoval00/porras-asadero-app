"""
VISTAS Y LÓGICA PARA RESPALDO Y RESTAURACIÓN DE BD
Compatible con SQLite y MySQL para Porras Asadero.
Permite crear respaldo completo (.sql) y restaurar desde archivo SQL con transacciones seguras.
"""
import os
import shutil
import sqlite3
import subprocess
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods


# ========== RUTAS Y DETECCIÓN DE BINARIOS MYSQL ==========
def buscar_binario(nombre_binario):
    """Busca un ejecutable en rutas conocidas de MySQL o en el PATH del sistema."""
    en_path = shutil.which(nombre_binario)
    if en_path:
        return en_path

    rutas_comunes = [
        r'C:\Program Files\MySQL\MySQL Server 8.4\bin',
        r'C:\Program Files\MySQL\MySQL Server 8.0\bin',
        r'C:\Program Files\MySQL\MySQL Server 5.7\bin',
        r'C:\xampp\mysql\bin',
        r'C:\wamp64\bin\mysql\mysql8.0.31\bin',
        r'C:\wamp64\bin\mysql\mysql5.7.36\bin',
        r'C:\laragon\bin\mysql\current\bin',
    ]

    for carpeta in rutas_comunes:
        ruta_completa = os.path.join(carpeta, nombre_binario)
        if os.path.isfile(ruta_completa):
            return ruta_completa

    return None


def obtener_info_base_datos():
    """Detecta el motor configurado en Django (SQLite o MySQL) y su estado."""
    db_config = settings.DATABASES['default']
    engine = db_config.get('ENGINE', '')
    es_sqlite = 'sqlite3' in engine
    es_mysql = 'mysql' in engine

    if es_sqlite:
        ruta_db = str(db_config.get('NAME', settings.BASE_DIR / 'db.sqlite3'))
        existe = os.path.isfile(ruta_db)
        tamano_mb = 0.0
        if existe:
            try:
                tamano_mb = round(os.path.getsize(ruta_db) / (1024 * 1024), 2)
            except Exception:
                pass

        return {
            'motor': 'SQLite',
            'es_sqlite': True,
            'es_mysql': False,
            'nombre': os.path.basename(ruta_db),
            'ruta': ruta_db,
            'conectado': existe,
            'tamano_mb': tamano_mb,
            'host': 'Local (Archivo)',
            'detalles': f'Base de datos local SQLite ({tamano_mb} MB)'
        }
    elif es_mysql:
        bin_mysql = buscar_binario('mysql.exe')
        bin_dump = buscar_binario('mysqldump.exe')
        host = db_config.get('HOST', 'localhost')
        puerto = str(db_config.get('PORT', 3306))
        usuario = db_config.get('USER', 'root')
        password = db_config.get('PASSWORD', '')
        nombre_db = db_config.get('NAME', 'porras_db')

        conectado = False
        if bin_mysql:
            try:
                cmd = [
                    bin_mysql,
                    '-h', host,
                    '-u', usuario,
                    '-P', str(puerto),
                    f'--password={password}',
                    '-e', 'SELECT 1;',
                    str(nombre_db)
                ]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
                conectado = (res.returncode == 0)
            except Exception:
                conectado = False

        return {
            'motor': 'MySQL',
            'es_sqlite': False,
            'es_mysql': True,
            'nombre': str(nombre_db),
            'host': f'{host}:{puerto}',
            'usuario': usuario,
            'password': password,
            'puerto': puerto,
            'bin_mysql': bin_mysql,
            'bin_dump': bin_dump,
            'conectado': conectado,
            'detalles': f'Servidor MySQL en {host}:{puerto}'
        }
    else:
        return {
            'motor': engine.split('.')[-1],
            'es_sqlite': False,
            'es_mysql': False,
            'nombre': str(db_config.get('NAME', 'Default')),
            'conectado': True,
            'host': 'Servidor Django',
            'detalles': 'Motor de base de datos genérico'
        }


# ========== VISTAS PRINCIPALES ==========
@login_required
@require_http_methods(["GET", "POST"])
def backup(request):
    """Muestra el panel de respaldo y gestiona la descarga del backup completo."""
    if request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return redirect('validar_permisos')

    info_db = obtener_info_base_datos()

    if request.method == "POST":
        accion = request.POST.get('accion')
        try:
            if accion == 'backup_completo':
                if not info_db['conectado']:
                    return JsonResponse({
                        'error': f"No se puede conectar a la base de datos ({info_db['motor']}). Verifica que esté activa y disponible."
                    }, status=400)

                if info_db['es_sqlite']:
                    return realizar_respaldo_sqlite(info_db)
                elif info_db['es_mysql']:
                    return realizar_respaldo_mysql(info_db)
                else:
                    return realizar_respaldo_sqlite(info_db)
        except Exception as e:
            return JsonResponse({'error': f'Error al generar el respaldo: {str(e)}'}, status=500)

    context = {
        'titulo': 'Copia de Seguridad y Restauración',
        'info_db': info_db,
        'mysql_conectado': info_db['conectado'],
        'ahora': datetime.now(),
    }
    return render(request, 'backup/menu.html', context)


@login_required
@require_http_methods(["POST"])
def restaurar_datos(request):
    """Restaura la base de datos desde un archivo .sql cargado por el usuario."""
    if request.user.rol != 'ADMIN' and not request.user.is_superuser:
        return JsonResponse({'error': 'No tienes permisos de Administrador para restaurar la base de datos.'}, status=403)

    if 'archivo' not in request.FILES:
        return JsonResponse({'error': 'No se proporcionó ningún archivo de respaldo.'}, status=400)

    archivo = request.FILES['archivo']

    if not archivo.name.lower().endswith('.sql'):
        return JsonResponse({'error': 'El archivo seleccionado debe tener extensión .sql'}, status=400)

    if archivo.size > 120 * 1024 * 1024:
        return JsonResponse({'error': 'El archivo de respaldo supera el límite de 120MB.'}, status=400)

    try:
        contenido_bytes = archivo.read()
        try:
            contenido_sql = contenido_bytes.decode('utf-8')
        except UnicodeDecodeError:
            contenido_sql = contenido_bytes.decode('latin-1')

        info_db = obtener_info_base_datos()

        if info_db['es_sqlite']:
            restaurar_sqlite_desde_sql(info_db, contenido_sql)
            mensaje = "Base de datos SQLite restaurada exitosamente. Se ha aplicado toda la estructura y datos."
        elif info_db['es_mysql']:
            restaurar_mysql_desde_sql(info_db, contenido_sql)
            mensaje = "Base de datos MySQL restaurada correctamente."
        else:
            restaurar_sqlite_desde_sql(info_db, contenido_sql)
            mensaje = "Base de datos restaurada correctamente."

        return JsonResponse({'exito': True, 'mensaje': mensaje})

    except Exception as e:
        return JsonResponse({'error': f'Error al restaurar: {str(e)}'}, status=500)


# ========== IMPLEMENTACIÓN DE RESPALDO ==========
def realizar_respaldo_sqlite(info_db):
    """Genera un archivo SQL completo con esquema y datos desde SQLite."""
    ruta_db = info_db['ruta']
    timestamp_humano = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Encabezado SQL
    cabecera = [
        f"-- ========================================================",
        f"-- PORRAS ASADERO - RESPALDO COMPLETO DE BASE DE DATOS",
        f"-- Motor: SQLite ({info_db['nombre']})",
        f"-- Fecha y Hora: {timestamp_humano}",
        f"-- Tipo: Completo (Estructura DDL + Registros DML)",
        f"-- ========================================================\n",
        "PRAGMA foreign_keys=OFF;\nBEGIN TRANSACTION;\n"
    ]

    try:
        conn = sqlite3.connect(ruta_db)
        piezas = []
        for linea in conn.iterdump():
            # Omitir transacciones anidadas si iterdump las genera
            if linea in ('BEGIN TRANSACTION;', 'COMMIT;'):
                continue
            piezas.append(linea)
        conn.close()

        cuerpo = "\n".join(piezas)
        cierre = "\nCOMMIT;\nPRAGMA foreign_keys=ON;\n"
        contenido_sql = "\n".join(cabecera) + cuerpo + cierre

        return generar_archivo_descarga(contenido_sql, f"respaldo_porras_{info_db['nombre']}")
    except Exception as e:
        raise Exception(f"No fue posible volcar la base de datos SQLite: {str(e)}")


def realizar_respaldo_mysql(info_db):
    """Genera un archivo SQL completo con mysqldump."""
    bin_dump = info_db.get('bin_dump')
    if not bin_dump:
        raise Exception("No se encontró el ejecutable mysqldump.exe en el sistema.")

    timestamp_humano = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cmd = [
        bin_dump,
        '-h', info_db['host'].split(':')[0],
        '-u', info_db['usuario'],
        '-P', str(info_db['puerto']),
        f"--password={info_db['password']}",
        '--add-drop-table',
        '--complete-insert',
        '--single-transaction',
        info_db['nombre']
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode != 0:
            raise Exception(f"mysqldump falló: {res.stderr}")

        sql_content = res.stdout
        if not sql_content.strip():
            raise Exception("El archivo de respaldo generado está vacío.")

        cabecera = (
            f"-- ========================================================\n"
            f"-- PORRAS ASADERO - RESPALDO COMPLETO DE BASE DE DATOS\n"
            f"-- Motor: MySQL ({info_db['nombre']})\n"
            f"-- Fecha y Hora: {timestamp_humano}\n"
            f"-- Tipo: Completo (Estructura DDL + Registros DML)\n"
            f"-- ========================================================\n\n"
        )
        return generar_archivo_descarga(cabecera + sql_content, f"respaldo_porras_{info_db['nombre']}")
    except subprocess.TimeoutExpired:
        raise Exception("Tiempo de espera agotado al generar el respaldo de MySQL.")


# ========== IMPLEMENTACIÓN DE RESTAURACIÓN ==========
def restaurar_sqlite_desde_sql(info_db, contenido_sql):
    """Ejecuta el script SQL en la base de datos SQLite con respaldo de seguridad temporal."""
    ruta_db = info_db['ruta']
    ruta_bak = ruta_db + '.bak_restauracion'

    # 1. Crear copia de seguridad antes de modificar
    if os.path.exists(ruta_db):
        shutil.copy2(ruta_db, ruta_bak)

    # 2. Cerrar conexiones activas de Django
    try:
        connection.close()
    except Exception:
        pass

    try:
        conn = sqlite3.connect(ruta_db, timeout=20)
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys = OFF;")
        cursor.executescript(contenido_sql)
        conn.commit()
        conn.close()

        # Si todo salió bien, eliminar el archivo de seguridad temporal
        if os.path.exists(ruta_bak):
            try:
                os.remove(ruta_bak)
            except Exception:
                pass
    except Exception as e:
        # Revertir si ocurrió un fallo
        if os.path.exists(ruta_bak):
            shutil.copy2(ruta_bak, ruta_db)
            try:
                os.remove(ruta_bak)
            except Exception:
                pass
        raise Exception(f"Fallo al ejecutar el script SQL sobre SQLite: {str(e)}")


def restaurar_mysql_desde_sql(info_db, contenido_sql):
    """Importa el script SQL en el servidor MySQL mediante mysql.exe."""
    bin_mysql = info_db.get('bin_mysql')
    if not bin_mysql:
        raise Exception("No se encontró el ejecutable mysql.exe en el sistema.")

    cmd = [
        bin_mysql,
        '-h', info_db['host'].split(':')[0],
        '-u', info_db['usuario'],
        '-P', str(info_db['puerto']),
        f"--password={info_db['password']}",
        info_db['nombre']
    ]

    try:
        proceso = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proceso.communicate(input=contenido_sql, timeout=120)

        if proceso.returncode != 0:
            raise Exception(f"Error MySQL: {stderr}")
        return True
    except subprocess.TimeoutExpired:
        raise Exception("Tiempo de espera agotado al restaurar la base de datos MySQL.")


def generar_archivo_descarga(contenido_sql, prefijo):
    """Genera la respuesta HTTP con el archivo descargable .sql."""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nombre_archivo = f"{prefijo}_{timestamp}.sql"
    response = HttpResponse(contenido_sql.encode('utf-8'), content_type='application/sql; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'
    return response
