import base64
import os
import time
from dateutil import relativedelta
from dateutil.parser import parse
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xlsxwriter
from io import BytesIO
from datetime import datetime

from odoo.tools import formatLang


class WizardIRT(models.TransientModel):
    _name = 'wizard.irt'
    _description = 'Print IRT Map'
    _rec_name = "company_id"

    slip_filter_by = fields.Selection([
        ('payslip_batch', 'Payslip Batch'),
        ('payslip_date', 'Payslip Date'),
        ('year', 'Fiscal Year')
    ], 'Filter By', required=True,
        help='Select the methond to capture the Payslips. You can choose Payslip Batch or by Date')
    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for wich you want do generate the Salary map Report')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    company_id = fields.Many2one("res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)

    fiscal_year = fields.Integer('Fiscal Year')
    group = fields.Selection([('group_a', 'Grupo A'), ('group_bc', 'Grupo B - C')], string='Group', default='group_a')
    report_type = fields.Selection([('pdf', 'PDF'), ('excel', 'Excel')], string='Report Type', default='pdf')

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be lower than End Date')

    def print_report(self):
        data = {
            'form': self.read([
                'group', 'slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'fiscal_year'
            ])[0]
        }
        if self.group == 'group_a':
            return self.env.ref('l10n_ao_hr.action_report_irt_group_a').report_action(self, data=data)
        elif self.group == 'group_bc':
            return self.env.ref('l10n_ao_hr.action_report_irt_group_bc').report_action(self, data=data)

    # def print_report(self):
    #     return self.env.ref('ao_hr.action_report_irt').report_action(self, data={
    #         'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'fiscal_year'])[0]})

    def _get_report_values(self):
        fiscal_year = 0
        docs = period_date = contracts = slip_obj = None
        result = {'subject': 0, 'no_subject': 0, 'exempt': 0, 'tax': 0}
        slip_filter_by = self.slip_filter_by

        group_irt = self.group
        if slip_filter_by == 'payslip_batch':
            slip_id = self.hr_payslip_run_id.id
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            period_date = parse(str(self.env['hr.payslip.run'].browse(slip_id).date_end))
        elif slip_filter_by == 'payslip_date':
            start_date = self.start_date
            end_date = self.end_date
            period_date = parse(str(end_date))
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)])
        elif slip_filter_by == 'year':
            docs = self.env['hr.payslip']
            fiscal_year = self.fiscal_year
            for doc in self.env['hr.payslip'].search([]):
                if doc.date_from.year == fiscal_year:
                    docs += doc
        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        contracts = docs.mapped('contract_id').filtered(lambda l: l.struct_id.code == 'BASE')
        for contract in contracts:
            _irt_subject = _irt_not_subject = _irt_exempt = _irt_tax = 0
            if group_irt == 'group_a' and contract.struct_id.code == 'BASE':
                for slip in docs.filtered(lambda r: r.contract_id == contract):
                    _irt_subject += slip.amount_base_irt
                    _irt_not_subject += (slip.amount_inss * -1)
                    _irt_exempt = (slip._amount_irt_exempt())
                    _irt_tax = (slip.amount_irt * -1)
                result[contract.id] = [{
                    'subject': _irt_subject,
                    'no_subject': _irt_not_subject,
                    'exempt': _irt_exempt,
                    'tax': _irt_tax
                }]
        if not result:
            raise ValidationError('There are no contracts for A class employees')

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'slip_run': slip_obj or docs[-1],
            'contracts': contracts,
            'data': result,
            'time': time,
            'fiscal_year': fiscal_year,
            'slip_filter': slip_filter_by,
            'irt_group': group_irt,
            'formatLang': formatLang,
            'env': self.env,
            'date': {'start': self.start_date, 'end': self.end_date},
        }

    def print_report_excel(self):
        report_values = self._get_report_values()

        data_atual = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        nome_arquivo = f'Mapa_de_IRT_Excel_{data_atual}.xlsx'

        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        temp_logo_path = None
        logo = self.env.user.company_id.logo
        if logo:
            logo_binary = base64.b64decode(logo)

            temp_logo_path = '/tmp/logo_temp.png'
            with open(temp_logo_path, 'wb') as temp_logo_file:
                temp_logo_file.write(logo_binary)

            sheet.insert_image('A1', temp_logo_path,
                               {'x_offset': 5, 'y_offset': 5, 'x_scale': 0.5, 'y_scale': 0.5, 'positioning': 2})

        cabecalho_format = workbook.add_format({'bold': True})

        cabecalho_info = [
            'Dirigida a AGT',
            f'EMPRESA: {self.env.user.company_id.name}',
            f'Endereço: {self.env.user.company_id.street}',
            f'NIF: {self.env.user.company_id.vat}',
            f'TEL: {self.env.user.company_id.mobile}',
        ]

        for i, info in enumerate(cabecalho_info):
            sheet.write(i + 6, 0, info, cabecalho_format)  # Inicia da linha 7 (A7) para cabecalho_info

        linha_atual = len(cabecalho_info) + 6

        if self.slip_filter_by == 'payslip_batch':
            info_acima_tabela = f'MAPA DE IRT DO MÊS DE {report_values.get("slip_run").name}'.upper()
        elif self.slip_filter_by == 'payslip_date':
            info_acima_tabela = f'MAPA DE IRT DE {self.start_date} ATÈ {self.end_date}'
        elif self.slip_filter_by == 'year':
            info_acima_tabela = f'MAPA DE IRT DE {self.fiscal_year}'

        sheet.merge_range(linha_atual, 2, linha_atual, 7, info_acima_tabela, cabecalho_format)

        linha_atual += 2

        cabecalhos = ['ID', 'NIF Trabalhador', 'Nome', 'Segurança Social', 'Provincia', 'Municipio',
                      'Salario Base', 'Desconto por Falta', 'Subsídio Alimentação',
                      'Subsídio Transporte', 'Abono Família', 'Reembolso de Despesas',
                      'Outros', 'Cálculo Manual de Excesso de Subsídios ?',
                      'Excesso Subsídios Não Sujeitos', 'Abono de Falhas',
                      'Subsídio Renda de Casa', 'Compensação Por Rescisão',
                      'Subsídio de Férias', 'Horas Extras', 'Subsídio de Atavio',
                      'Subsídio de Representação', 'Prémios', 'Subsídio de Natal',
                      'Outros Subsídios Sujeitos', 'Salário Ilíquido',
                      'Registo Manual de Contribuição Segurança Social?',
                      'Base Tributável Segurança Social',
                      'Não Sujeito a Segurança Social?', 'Contribuição Segurança Social',
                      'Base Tributável IRT', 'Insento IRT?',
                      'IRT Apurado']

        cabecalho_tabela_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border':1})

        for coluna, cabecalho in enumerate(cabecalhos):
            sheet.write(linha_atual, coluna, cabecalho, cabecalho_tabela_format)

        order_number = 1

        cell_border = workbook.add_format({'border': 1})

        for linha, payslip in enumerate(report_values['docs'], start=linha_atual + 1):
            sheet.write(linha, 0, order_number, cell_border)
            sheet.write(linha, 1, payslip.employee_id.fiscal_number if payslip.employee_id.fiscal_number else None, cell_border)
            sheet.write(linha, 2, payslip.employee_id.name, cell_border)
            sheet.write(linha, 3, payslip.employee_id.social_security if payslip.employee_id.social_security else None, cell_border)
            sheet.write(linha, 4, payslip.employee_id.location_province.code if payslip.employee_id.location_province else None, cell_border)
            sheet.write(linha, 5, payslip.employee_id.location_province.name if payslip.employee_id.location_province else None, cell_border)
            sheet.write(linha, 6, sum([line.total for line in payslip.line_ids if line.code == 'BASE']), cell_border)
            sheet.write(linha, 7, [payslip.misses * -1] if payslip.misses else 0.0, cell_border)
            sheet.write(linha, 8, payslip.sub_ali, cell_border)
            sheet.write(linha, 9, payslip.sub_trans, cell_border)
            sheet.write(linha, 10, payslip.sub_fam, cell_border) # Abono Família
            sheet.write(linha, 11, sum([line.total for line in payslip.line_ids if line.category_id.code == 'remb_despesa']), cell_border) # Reembolso de Despesas

            sub_codes = ['sub_ali', 'sub_trans', 'sub_fam', 'BASE', 'sub_fal', 'sub_nat', 'premio','sub_represent' ,'sub_atav','remb_despesa', 'sub_renda', 'recisao', 'sub_fer', 'HE']
            outros_sub = sum([line.total for line in payslip.line_ids if line.code not in sub_codes and line.total > 0])
            sheet.write(linha, 12, outros_sub, cell_border) # Outros
            sheet.write(linha, 13, "N", cell_border) # Cálculo Manual de Excesso de Subsídios ?

            excesso_sub_suj = ((payslip.sub_ali + payslip.sub_trans) - 60000)
            sheet.write(linha, 14, excesso_sub_suj if excesso_sub_suj > 0 else 0, cell_border) # Excesso Subsídios Não Sujeitos
            sheet.write(linha, 15, sum([line.total for line in payslip.line_ids if line.code == 'sub_fal']), cell_border)
            sheet.write(linha, 16, sum([line.total for line in payslip.line_ids if line.code == 'sub_renda']), cell_border)
            sheet.write(linha, 17, sum([line.total for line in payslip.line_ids if line.code == 'recisao']), cell_border) # sub de recisao
            sheet.write(linha, 18, sum([line.total for line in payslip.line_ids if line.code == 'sub_fer']), cell_border)
            sheet.write(linha, 19, sum([line.total for line in payslip.line_ids if line.code == 'HE']), cell_border)
            sheet.write(linha, 20, sum([line.total for line in payslip.line_ids if line.code == 'sub_atav']), cell_border) # Subsídio de Atavio
            sheet.write(linha, 21, sum([line.total for line in payslip.line_ids if line.code == 'sub_represent']), cell_border) # Subsídio de Representação
            sheet.write(linha, 22, sum([line.total for line in payslip.line_ids if line.code == 'premio']), cell_border) # Premios
            sheet.write(linha, 23, sum([line.total for line in payslip.line_ids if line.code == 'sub_nat']), cell_border)
            sheet.write(linha, 24, sum([line.total for line in payslip.line_ids if line.code not in ['sub_ali', 'sub_trans', 'BASE'] and line.total > 0]), cell_border) # Outros Subsídios Sujeitos
            sheet.write(linha, 25, payslip.total_remunerations, cell_border)
            sheet.write(linha, 26, "N", cell_border)
            sheet.write(linha, 27, sum([(line.total * -1) for line in payslip.line_ids if line.code == 'ss_collect']), cell_border) # Base Tributável Segurança Social
            sheet.write(linha, 28, "N" if payslip.amount_inss else "S", cell_border)
            sheet.write(linha, 29, payslip.amount_inss, cell_border)
            sheet.write(linha, 30, payslip.amount_base_irt, cell_border) # Base Tributável IRT
            sheet.write(linha, 31, "N" if payslip.amount_irt != 0.0 else "S", cell_border)
            sheet.write(linha, 32, (payslip.amount_irt * -1 if payslip.amount_irt else 0.0), cell_border)


            order_number += 1

        # Ajuste a largura das colunas automaticamente tendo conta o cabecalho
        for coluna, cabecalho in enumerate(cabecalhos):
            sheet.set_column(coluna, coluna, len(cabecalho) + 2)
        workbook.close()
        output.seek(0)

        os.remove(temp_logo_path)

        base64_content = base64.b64encode(output.read())

        temp_file = self.env['ir.attachment'].create({
            'name': nome_arquivo,
            'datas': base64_content,
            'store_fname': nome_arquivo,
            'type': 'binary',
        })

        # Retorna um link para o arquivo temporário
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{temp_file.id}?download=true&filename={nome_arquivo}',
            'target': 'self',
        }
