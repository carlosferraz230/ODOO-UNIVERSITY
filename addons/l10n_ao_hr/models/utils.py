import pandas as pd
from io import BytesIO
import os
bio = BytesIO()


def generate_xls(data_values, sheet_name):
    template = {'NR ORD': [], 'NOME': [], 'CODIGO DEP': [], 'Nº INSS': [], 'POSICAO': [], 'SALARIO BASE': [],
                'DESCONTO DE FALTAS E ATRASOS': [], 'Subsídio Alimentação': [], 'Subsídio Transporte': [],
                'Subsídio de Férias': [], 'Abono de Familia': [], 'Subsídio de Natal': [],
                'TOTAL SUBSIDIOS': [], 'SALARIO ILIQUIDO': [], 'TAXA SS': [], 'REMUNERAÇÃO TRIBUTAVEL': [],
                'IRT': [], 'AVANCO SALARIO': [], 'EMPRESTIMO/LOAN': [], 'FATURAS DE SAÚDE': [], 'OUTROS DESCONTOS': [],
                'TOTAL DESCONTO': [], 'PERCENTAGEM %': [], 'SALARIO LIQUIDO': [], }
    for i in data_values:
        template['NR ORD'].append(i['n'])
        template['NOME'].append(i['name'])
        template['CODIGO DEP'].append(i['departament'])
        template['Nº INSS'].append(i['n_ss'])
        template['POSICAO'].append(i['job'])
        template['SALARIO BASE'].append(i['wage'])
        template['DESCONTO DE FALTAS E ATRASOS'].append(i['desc_faltas'])
        template['Subsídio Alimentação'].append(i['sub_ali'])
        template['Subsídio Transporte'].append(i['sub_trans'])
        template['Abono de Familia'].append(i['sub_fam'])
        template['Subsídio de Férias'].append(i['sub_ferias'])
        template['Subsídio de Natal'].append(i['sub_nat'])
        template['TOTAL SUBSIDIOS'].append(i['total_sub'])
        template['SALARIO ILIQUIDO'].append(i['gross_salary'])
        template['TAXA SS'].append(i['ss_tax'])
        template['REMUNERAÇÃO TRIBUTAVEL'].append(i['rem_tribut'])
        template['IRT'].append(i['irt'])
        template['AVANCO SALARIO'].append(i['salary_advance'])
        template['EMPRESTIMO/LOAN'].append(i['loan'])
        template['FATURAS DE SAÚDE'].append(i['fact_saude'])
        template['OUTROS DESCONTOS'].append(i['outros_desc'])
        template['TOTAL DESCONTO'].append(i['total_deductions'])
        template['PERCENTAGEM %'].append(i['percentage'])
        template['SALARIO LIQUIDO'].append(i['net_salary'])

    result = pd.DataFrame(data=template)
    result.to_excel(os.path.expanduser('~' + '/salary_map.xlsx'), sheet_name=sheet_name, index=False)


def read_xls():
    with open(os.path.expanduser('~' + '/salary_map.xlsx'), 'rb') as file:
        return file.read()

