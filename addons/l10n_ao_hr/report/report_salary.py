# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from . import report_common


class ReportSalary(models.AbstractModel):
    _name = 'report.l10n_ao_hr.report_salary'
    _description = "Salary Report Sheet"

    @api.model
    def _get_report_values(self, docids, data=None):
        slip_obj = docs = period_date_obj = None
        print(data)
        slip_filter_by = data['form']['slip_filter_by']

        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            period_date = self.env['hr.payslip.run'].browse(slip_id).date_end
        else:
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            slip_id = data['form']['hr_payslip_run_id'][0]
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            period_date = start_date
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)])

        if not docs:
            raise ValidationError('There is no payslips that match this criteria')
        return {
            'doc_ids': docs.ids,
            'doc_model': 'hr.payslip',
            'docs': docs,
            'time': time,
            'slip_run': slip_obj,
            'formatLang': formatLang,
            'filter_by': slip_filter_by,
            'env': self.env,
            'period': '%s de %d' % (report_common.get_month_text(period_date.month), period_date.year)
        }
