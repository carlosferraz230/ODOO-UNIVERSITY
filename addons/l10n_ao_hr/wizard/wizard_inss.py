import base64
import os
import time
from datetime import datetime
from dateutil import relativedelta
from dateutil.parser import parse
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import xlsxwriter
from io import BytesIO
from PIL import Image
from datetime import datetime

from odoo.tools import formatLang


class WizardINSS(models.TransientModel):
    _name = 'wizard.inss'
    _description = 'Print INSS Map'
    _rec_name = "company_id"

    slip_filter_by = fields.Selection([('payslip_batch', 'Payslip Batch'), ('payslip_date', 'Payslip Date')],
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

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError('Start Date must be lower than End Date')

    def print_report(self):
        data = {'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date'])[0]}
        return self.env.ref('l10n_ao_hr.action_report_inss').report_action(self, data=data)

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
        report_values = self._get_report_values()

        data_atual = fields.Datetime.now().strftime('%Y%m%d%H%M%S')
        nome_arquivo = f'Relatorio_INSS_Excel_{data_atual}.xlsx'

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
            'Dirigida a INSS',
            f'EMPRESA: {self.env.user.company_id.name}',
            f'Endereço: {self.env.user.company_id.street}',
            f'NIF: {self.env.user.company_id.vat}',
            f'TEL: {self.env.user.company_id.mobile}',
        ]

        for i, info in enumerate(cabecalho_info):
            sheet.write(i + 6, 0, info, cabecalho_format)  # Inicia da linha 7 (A7) para cabecalho_info

        linha_atual = len(cabecalho_info) + 6

        info_acima_tabela = f'MAPA DE SALÁRIO DO MÊS DE {report_values.get("period")}'.upper()
        sheet.merge_range(linha_atual, 2, linha_atual, 7, info_acima_tabela, cabecalho_format)

        linha_atual += 2

        cabecalhos = ['ID', 'Nome', 'Sign Post', 'Salário Base', 'Remuneração', 'Salário Liquido',
                      'SS Trabalhador 3%', 'SS Partonal 8%']

        cabecalho_tabela_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})

        for coluna, cabecalho in enumerate(cabecalhos):
            sheet.write(linha_atual, coluna, cabecalho, cabecalho_tabela_format)

        order_number = 1

        for linha, payslip in enumerate(report_values['docs'], start=linha_atual + 1):
            sheet.write(linha, 0, order_number)
            sheet.write(linha, 1, payslip.employee_id.name)
            if payslip.employee_id.category_ids:
                sheet.write(linha, 2, payslip.employee_id.category_ids[0].name)
            sheet.write(linha, 3, formatLang(self.env, (payslip.remuneration - (payslip.misses * -1))))
            sheet.write(linha, 4, formatLang(self.env, (payslip.allowance + payslip.contract_id.abo_fam_ss())))
            sheet.write(linha, 5, formatLang(self.env, (payslip.remuneration - (payslip.misses * -1)) + (
                    payslip.allowance + payslip.contract_id.abo_fam_ss())))
            sheet.write(linha, 6, formatLang(self.env, (payslip.amount_inss * -1)))
            sheet.write(linha, 7, formatLang(self.env, (
                    (payslip.remuneration + payslip.allowance + payslip.contract_id.abo_fam_ss()) - (
                    payslip.misses * -1)) * 0.08))

            order_number += 1

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
