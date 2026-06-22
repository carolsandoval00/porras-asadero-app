import ast
import re
import os
import sys

# Archivos a refactorizar (según el reporte)
TARGET_FILES = [
    r".\pago\views.py",
    r".\pedidos\views.py",
    r".\reservas\views.py",
    r".\usuarios\views.py",
]

def refactor_render_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    new_lines = lines[:]
    changes = 0
    offset = 0  # ajuste por líneas insertadas

    # Patrón: return render(request, 'algo.html', {...})
    # Puede ser multilínea, así que trabajamos con el texto completo
    # Buscamos todas las ocurrencias con regex
    pattern = re.compile(
        r'(?P<indent>[ \t]*)return render\((?P<args>request,\s*[\'"][^\'"]+[\'"]\s*,\s*\{[^}]*\})\)',
        re.DOTALL
    )

    def replace_render(match):
        nonlocal changes
        indent = match.group('indent')
        args = match.group('args')

        # Separar: request, 'template', {...}
        # Extraer template y dict
        inner_match = re.match(
            r'request,\s*(?P<template>[\'"][^\'"]+[\'"])\s*,\s*(?P<dict>\{[^}]*\})',
            args,
            re.DOTALL
        )
        if not inner_match:
            return match.group(0)  # no tocar si no matchea bien

        template = inner_match.group('template')
        dict_str = inner_match.group('dict')

        # Limpiar el dict (quitar saltos de línea extra)
        dict_clean = re.sub(r'\s+', ' ', dict_str).strip()

        changes += 1
        return f"{indent}context = {dict_clean}\n{indent}return render(request, {template}, context)"

    new_content = pattern.sub(replace_render, content)

    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"[OK] {filepath}: {changes} render(s) refactorizados.")
    else:
        print(f"[INFO] {filepath}: No se encontraron renders con diccionario.")

    return changes


def main():
    base_dir = os.getcwd()
    total = 0

    print("=" * 60)
    print("REFACTOR: return render(..., {dict}) → context + render")
    print("=" * 60)

    for rel_path in TARGET_FILES:
        filepath = os.path.join(base_dir, rel_path.lstrip('.\\').lstrip('./'))
        filepath = os.path.normpath(filepath)

        if not os.path.exists(filepath):
            print(f"[ERROR] No encontrado: {filepath}")
            continue

        total += refactor_render_in_file(filepath)

    print("=" * 60)
    print(f"TOTAL renders refactorizados: {total}")
    print("=" * 60)


if __name__ == '__main__':
    main()