from odoo import fields, models, api , _


class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'

    @api.model
    def _get_default_rule_ids(self):
        return [
            (0, 0, {
                'name': _('Basic Salary'),
                'sequence': 1,
                'code': 'BAS',
                'category_id': self.env.ref('l10n_ao_hr_payroll.hr_salary_rule_category_base').id,
                'condition_select': 'none',
                'amount_select': 'code',
                'amount_python_compute': 'result = payslip.paid_amount',
             }),
        ]
