import pandas as pd
from io import BytesIO

bio = BytesIO()

def generate_xls(data_values):
    template = {'NR': [], 'NOME': [], 'POSICAO': [], 'SALARIO BASE': [], }
    for i in data_values:
        template['NR'].append(i['n'])
        template['NOME'].append(i['name'])
        template['POSICAO'].append(i['job'])
        template['SALARIO BASE'].append(i['wage'])

    result = pd.DataFrame(data=template)
    result.to_excel('/home/salary_map.xlsx', index=False)


def read_xls():
    with open("/home/salary_map.xlsx", 'rb') as file:
        return file.read()
