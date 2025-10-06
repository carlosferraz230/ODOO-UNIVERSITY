from odoo import fields, models, api


class SalaryRule(models.Model):
    _inherit = 'hr.salary.rule'
    _order = 'sequence'

    sequence_view = fields.Integer(string='Sequence', related='sequence')


class PayrollStructure(models.Model):
    _inherit = 'hr.payroll.structure'

    code = fields.Char(string='Reference', required=True)

    def _remove_rule_demo(self):
        """:@author: Hermenegildo Mulonga """
        salary_rules = self.env['hr.salary.rule'].search([('code', 'in', ['NET', 'BASIC', 'GROSS'])])
        salary_rule_categories = self.env['hr.salary.rule.category'].search([
            ('code', 'in', ['ALW', 'BASIC', 'GROSS', 'NET', 'HRA', 'DA', 'Travel', 'Meal', 'Medical', 'Other', 'COMP'])
        ])
        structures = self.env['hr.payroll.structure'].search([('code', '!=', ['BASE', 'CLASS_B', 'CLASS-B'])])
        if structures:
            structures.unlink()
        if salary_rules:
            salary_rules.unlink()
        if salary_rule_categories:
            salary_rule_categories.unlink()

    @api.model
    def _get_default_report_id(self):
        return self.env.ref('l10n_ao_hr.action_report_payslip_second', False)

    @api.model
    def _get_default_rule_ids(self):
        return False


class StructureType(models.Model):
    _inherit = 'hr.payroll.structure.type'

    type = fields.Selection([
        ('employee', 'Collaborator'), ('worker', 'Worker')
    ], string="Type", default='employee')
