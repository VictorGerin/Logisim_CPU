import os
import sys
import argparse

def get_files_with_extension(directory, ext):
    """Retorna lista de caminhos de arquivos com uma dada extensão."""
    result = []
    for r, d, fs in os.walk(directory):
        for f in fs:
            if f.endswith(ext):
                result.append(os.path.normpath(os.path.join(r, f)).replace(os.sep, '/'))
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--circuits-txt", action="store_true")
    parser.add_argument("--temp-txt", type=str, help="Caminho do build dir")
    parser.add_argument("--py", action="store_true")
    parser.add_argument("--py-with-json", action="store_true")
    args = parser.parse_args()

    circuits_dir = 'Circuits'

    if args.circuits_txt:
        # .txt que possuem um .json correspondente
        txt_files = get_files_with_extension(circuits_dir, '.txt')
        for txt in txt_files:
            json_path = txt[:-4] + '.json'
            if os.path.isfile(json_path):
                print(txt)

    elif args.temp_txt:
        # .txt do build/temp gerados por .py (ignorando se já existe um .txt no Circuits)
        build_temp = f"{args.temp_txt}/temp"
        
        # Coleta os nomes (stems) dos txt que já existem em Circuits
        txt_files = get_files_with_extension(circuits_dir, '.txt')
        existing_stems = set()
        for txt in txt_files:
            if os.path.isfile(txt[:-4] + '.json'):
                existing_stems.add(os.path.splitext(os.path.basename(txt))[0])

        py_files = get_files_with_extension(circuits_dir, '.py')
        for py in py_files:
            base_name = os.path.splitext(os.path.basename(py))[0]
            json_path = py[:-3] + '.json'
            if os.path.isfile(json_path) and base_name not in existing_stems:
                print(f"{build_temp}/{base_name}.txt")

    elif args.py:
        # Todos os .py
        for py in get_files_with_extension(circuits_dir, '.py'):
            print(py)

    elif args.py_with_json:
        # .py que possuem um .json correspondente
        for py in get_files_with_extension(circuits_dir, '.py'):
            json_path = py[:-3] + '.json'
            if os.path.isfile(json_path):
                print(py)

if __name__ == "__main__":
    main()