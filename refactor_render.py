import ast
import os
import warnings

def analizar_archivo(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=SyntaxWarning)
            tree = ast.parse(source, filename=filepath)
    except SyntaxError:
        return 0, 0, []

    total_renders = 0
    renders_with_dict = 0
    lineas_alerta = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Return):
            if isinstance(node.value, ast.Call):
                call = node.value
                func = call.func
                # Verificar que es render(...)
                es_render = (
                    (isinstance(func, ast.Name) and func.id == 'render') or
                    (isinstance(func, ast.Attribute) and func.attr == 'render')
                )
                if es_render:
                    total_renders += 1
                    # Verificar si el tercer argumento es un dict literal
                    if len(call.args) >= 3 and isinstance(call.args[2], ast.Dict):
                        renders_with_dict += 1
                        lineas_alerta.append(node.lineno)

    return total_renders, renders_with_dict, lineas_alerta


def main():
    base_dir = os.getcwd()
    print("-" * 50)

    total_archivos = 0
    total_renders = 0
    total_con_dict = 0

    for dirpath, dirnames, filenames in os.walk(base_dir):
        # Ignorar carpetas del entorno virtual y similares
        dirnames[:] = [d for d in dirnames if d not in ('venv', '.venv', 'env', '__pycache__', '.git', 'migrations')]

        for filename in filenames:
            if filename == 'views.py':
                filepath = os.path.join(dirpath, filename)
                rel = os.path.relpath(filepath, base_dir)
                total_archivos += 1

                renders, con_dict, lineas = analizar_archivo(filepath)
                total_renders += renders
                total_con_dict += con_dict

                if con_dict == 0:
                    print(f"[OK]     .\\{rel}: {renders} render(s) correctos.")
                else:
                    print(f"[ALERTA] .\\{rel}: Tiene {con_dict} render(s) en las líneas {lineas}.")

    print("-" * 50)
    print(f"\nREPORTE FINAL (SOLO LECTURA):")
    print(f"Archivos Python escaneados  : {total_archivos}")
    print(f"Total de 'return render'    : {total_renders}")
    print(f"Renders usando diccionario  : {total_con_dict}")
    print("-" * 50)


if __name__ == '__main__':
    main()