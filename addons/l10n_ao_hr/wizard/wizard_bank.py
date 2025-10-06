import base64
import time
from datetime import date
from datetime import datetime
from datetime import timedelta
from dateutil import relativedelta
from odoo.tools.translate import _
from odoo.exceptions import UserError
import calendar
from odoo.tools.misc import formatLang
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo import api, fields, models
import xlsxwriter
from io import BytesIO
from datetime import datetime
import tempfile
import os


class WizardSalary(models.TransientModel):
    _name = 'wizard.bank'
    _description = 'Print BANK Map'

    bank = fields.Many2one('res.bank', string='Bank', required='True', help='Select the bank for print the declaration')
    slip_filter_by = fields.Selection([('payslip_batch', 'Bayslip Batch'), ('payslip_date', 'Payslip Date')],
                                      'Filter By', required=True,
                                      help='Select the methond to capture the Payslips. You can choose Payslip Batch or by Date')
    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for wich you want do generate the Salary map Report')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    company_id = fields.Many2one("res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)
    report_type = fields.Selection([('pdf', 'PDF'), ('excel', 'Excel')], string='Report Type', default='pdf')

    def _check_dates(self):
        for payslip in self:
            if payslip.start_date > payslip.end_date:
                return False
        return True

    _constraints = [(_check_dates, "'Start Date' must be less than 'End Date'.", ['Start Date', 'End Date'])]

    def get_lines(self):
        for payslip in self:
            if payslip.slip_filter_by == 'payslip_batch':
                return [id for id in payslip.hr_payslip_run_id.slip_ids if id.employee_id.bank_bank == self.bank.id]
            else:
                return [id for id in self.env['hr.payslip'].search([('date_from', '>=', self.start_date),
                                                                    ('date_to', '<=', self.end_date),
                                                                    ('employee_id.bank_bank', '=', self.bank.id)])]

    def get_date(self):
        meses = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho', 'Julho', 'Agosto', 'Setembro', 'Outubro',
                 'Novembro', 'Dezembro']
        return 'Luanda aos %d de %s de %d' % (datetime.now().day, meses[datetime.now().month - 1], datetime.now().year)

    def print_report(self):
        data = {'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date', 'bank'])[0]}
        return self.env.ref('ao_hr.action_report_bank').report_action(self, data=data)

    def _get_report_values(self):
        docs = slip_obj = period_date_obj = None

        if self.slip_filter_by == 'payslip_batch':
            slip_id = self.hr_payslip_run_id.id
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            slip_obj = docs.mapped("payslip_run_id")
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_start
        else:
            start_date = self.start_date
            end_date = self.end_date
            slip_id = slip_id = self.hr_payslip_run_id.id
            period_date = parse(str(end_date))
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            slip_obj = docs.mapped("payslip_run_id")
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)])
        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        months = {
            1: _('January'),
            2: _('February'),
            3: _('March'),
            4: _('April'),
            5: _('May'),
            6: _('June'),
            7: _('July'),
            8: _('August'),
            9: _('September'),
            10: _('October'),
            11: _('November'),
            12: _('December'),
        }

        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'time': time,
            'formatLang': formatLang,
            'env': self.env,
            'slip_run': slip_obj,
            'period': '%s de %d' % (months[period_date.month], period_date.year)
        }

    def print_report_excel(self):
        # Chame a função _get_report_values para obter os dados
        report_values = self._get_report_values()

        # Nomeie o arquivo Excel com a data atual
        data_atual = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        nome_arquivo = f'Relatorio_Mapa_Banco_Excel_{data_atual}.xlsx'

        # Crie e salve o relatório Excel diretamente
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet()

        # Defina os cabeçalhos das colunas
        cabecalhos = ['ID', 'Nome', 'IBAN', 'Salario']

        # Formatação para os cabeçalhos
        cabecalho_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})

        # Escreva os cabeçalhos na primeira linha do arquivo Excel
        for coluna, cabecalho in enumerate(cabecalhos):
            sheet.write(0, coluna, cabecalho, cabecalho_format)

        order_number = 1

        # Escreva os dados nas linhas seguintes do arquivo Excel
        for linha, payslip in enumerate(report_values['docs'], start=1):

            sheet.write(linha, 0, order_number)
            sheet.write(linha, 1, payslip.employee_id.name)
            iban_original = payslip.employee_id.bank_iban
            formatted_iban = iban_original.replace(" ", "").replace(".", "")
            sheet.write(linha, 2, formatted_iban)
            sheet.write(linha, 3, payslip.total_paid)

            order_number +=1

        # Salve e feche o arquivo Excel
        workbook.close()
        output.seek(0)

        # Converta o conteúdo do BytesIO para base64
        base64_content = base64.b64encode(output.read())

        # Crie um arquivo temporário no sistema de arquivos do Odoo
        temp_file = self.env['ir.attachment'].create({
            'name': nome_arquivo,
            'datas': base64_content,
            'store_fname': nome_arquivo,
            'type': 'binary',
        })

        # Retorne um link para o arquivo temporário
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{temp_file.id}?download=true&filename={nome_arquivo}',
            'target': 'self',
        }
