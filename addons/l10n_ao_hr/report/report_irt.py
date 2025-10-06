# -*- coding: utf-8 -*-

import time
from odoo import api, models, fields, _
from dateutil.parser import parse
from odoo.exceptions import ValidationError
from odoo.tools.misc import formatLang
from . import report_common


class ReportIRT(models.AbstractModel):
    _name = 'report.l10n_ao_hr.report_irt'
    _description = "IRT Group A Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        fiscal_year = 0
        docs = period_date = contracts = slip_obj = None
        result = {'subject': 0, 'no_subject': 0, 'exempt': 0, 'tax': 0}
        slip_filter_by = data['form']['slip_filter_by']

        group_irt = data['form']['group']
        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            period_date = parse(str(self.env['hr.payslip.run'].browse(slip_id).date_end))
        elif slip_filter_by == 'payslip_date':
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            period_date = parse(str(end_date))
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)])
        elif slip_filter_by == 'year':
            docs = self.env['hr.payslip']
            fiscal_year = data['form']['fiscal_year']
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
            'date': {'start': data['form']['start_date'], 'end': data['form']['end_date']},
            'period': '%s de %d' % (
                report_common.get_month_text(period_date.month), period_date.year) if period_date else 0.0
        }


class ReportIRTBC(models.AbstractModel):
    _name = 'report.l10n_ao_hr.report_irt_group_bc'
    _description = "IRT Group BC Report "

    @api.model
    def _get_report_values(self, docids, data=None):
        fiscal_year = 0
        docs = period_date = contracts = slip_obj = None
        result = {}
        slip_filter_by = data['form']['slip_filter_by']

        group_irt = data['form']['group']
        if slip_filter_by == 'payslip_batch':
            slip_id = data['form']['hr_payslip_run_id'][0]
            slip_obj = self.env['hr.payslip.run'].search([('id', '=', slip_id)])
            docs = self.env['hr.payslip'].search([('payslip_run_id', '=', slip_id)])
            period_date = parse(str(self.env['hr.payslip.run'].browse(slip_id).date_end))
        elif slip_filter_by == 'payslip_date':
            start_date = data['form']['start_date']
            end_date = data['form']['end_date']
            period_date = parse(str(end_date))
            docs = self.env['hr.payslip'].search([('date_to', '>=', start_date), ('date_to', '<=', end_date)])
        elif slip_filter_by == 'year':
            docs = self.env['hr.payslip']
            fiscal_year = data['form']['fiscal_year']
            for doc in self.env['hr.payslip'].search([]):
                if doc.date_from.year == fiscal_year:
                    docs += doc
        if not docs:
            raise ValidationError('There is no payslips that match this criteria')

        contracts = docs.mapped('contract_id').filtered(lambda l: l.struct_id.code == 'CLASS_B')
        for contract in contracts:
            _irt_subject = _irt_not_subject = _irt_exempt = _irt_tax = 0
            if group_irt == 'group_bc' and contract.struct_id.code == 'CLASS_B':
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
            raise ValidationError('There are no contracts for BC class employees')

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
            'date': {'start': data['form']['start_date'], 'end': data['form']['end_date']},
            'period': '%s de %d' % (
                report_common.get_month_text(period_date.month), period_date.year) if period_date else 0.0
        }
