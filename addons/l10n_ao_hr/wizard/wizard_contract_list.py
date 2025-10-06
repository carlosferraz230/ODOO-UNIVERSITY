import time
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse
from odoo.tools.misc import formatLang
from ..report import report_common


class WizardContractList(models.TransientModel):
    _name = 'wizard.contract.list'
    _description = 'Contract List Wizard'

    company_id = fields.Many2one("res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)
    departments = fields.Many2many("hr.department",string="Departments")
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('open', 'In execution'),
                   ('close','Expired'),
                   ('cancel','Cancel')], default="open")

    def get_domain(self):
        domain = [('state','=',self.state)]
        if self.departments:
            domain.append(('department_id','in',self.departments.ids))
        return domain

    def get_all_employee_contract(self):
        domain = self.get_domain()
        return self.env['hr.contract'].search(domain)

    def print_report(self):
        return self.env.ref('ao_hr.report_employee_contract_list').report_action(self)
