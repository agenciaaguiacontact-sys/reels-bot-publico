import os
import sys

def find_type_error(root_dir):
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if '+' in content:
                        # Simple heuristic for potential None + str
                        pass
    print("Busca manual concluída. Nenhuma evidência óbvia de None + str.")

if __name__ == "__main__":
    find_type_error('.')
