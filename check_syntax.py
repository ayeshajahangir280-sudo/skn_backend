import ast
import sys

files_to_check = [
    'api/emails.py',
    'api/views.py'
]

for file in files_to_check:
    try:
        with open(file, 'r') as f:
            ast.parse(f.read())
        print(f'{file}: OK')
    except SyntaxError as e:
        print(f'{file}: SYNTAX ERROR - {e}')
        sys.exit(1)

print('All files have valid syntax!')
