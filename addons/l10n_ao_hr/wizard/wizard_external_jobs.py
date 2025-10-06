import time
from odoo import fields, models, api
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import ValidationError, Warning


class WizardEmployeeExternalJobs(models.Model):
    _name = 'wizard.employee.external.jobs'
    _description = 'Employee External Jobs'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    employee_contract_id = fields.Many2one('hr.contract', string='Contract', related='employee_id.contract_id')
    remuneration_id = fields.Many2one('hr.remuneration.code', string='Remunerations for this Contract')
    percentage = fields.Float("External Jobs Percentage", default=0.0)

    def button_add_remuneration(self):
        contract = self.employee_contract_id
        if contract:
            values = {
                'remuneration_ids': [(0, 0, {
                    'remunerationcode_id': self.remuneration_id.id,
                    'rem_type': self.remuneration_id.type,
                    'date_start': self.start_date,
                    'date_end': self.end_date,
                    'amount': self.compute_remuneration_percentage(self.percentage),
                    'name': self.remuneration_id.name
                })]
            }
            contract.write(values)

    def compute_remuneration_percentage(self, percentage):
        contract = self.employee_contract_id
        amount = (contract.wage * percentage) / 100
        return amount
