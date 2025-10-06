import time
from odoo import fields, models, api
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import ValidationError, Warning


class WizardEmployeeExtract(models.TransientModel):
    _name = 'wizard.employee.extract'
    _description = 'Employee extract'

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        if self.start_date > self.end_date:
            raise ValidationError('Start Date must be lower than End Date')

    def get_employee_payslip(self):
        payslips = self.env['hr.payslip'].search(
            [('employee_id', '=', self.employee_id.id), ('date_from', '>=', self.start_date),
             ('date_to', '<=', self.end_date), ('state', 'not in', ['cancel'])], order='number asc')
        return payslips

    def print_report(self):
        return self.env.ref('l10n_ao_hr.report_employee_extract').report_action(self)
