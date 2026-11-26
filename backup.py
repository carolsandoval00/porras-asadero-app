"""
Módulo wrapper para respaldo.
Redirige a la lógica central de la app 'backup' para compatibilidad total con importaciones directas.
"""
from backup.views import (
    obtener_info_base_datos,
    buscar_binario,
    backup,
    restaurar_datos,
    realizar_respaldo_sqlite,
    realizar_respaldo_mysql,
    restaurar_sqlite_desde_sql,
    restaurar_mysql_desde_sql,
    generar_archivo_descarga,
)

__all__ = [
    'obtener_info_base_datos',
    'buscar_binario',
    'backup',
    'restaurar_datos',
    'realizar_respaldo_sqlite',
    'realizar_respaldo_mysql',
    'restaurar_sqlite_desde_sql',
    'restaurar_mysql_desde_sql',
    'generar_archivo_descarga',
]
