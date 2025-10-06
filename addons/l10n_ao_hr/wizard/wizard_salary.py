import time
from datetime import datetime
from dateutil import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from dateutil.parser import parse
from odoo.tools.misc import formatLang
from ..report import report_common


class WizardSalary(models.TransientModel):
    _name = 'wizard.salary'
    _description = 'Print Salary Map'
    _rec_name = "company_id"

    slip_filter_by = fields.Selection([
        ('payslip_batch', 'Bayslip Batch'), ('payslip_date', 'Payslip Date')
    ], 'Filter By', required=True, help='Select the method to capture the Payslips. You can choose Payslip Batch or by Date')
    hr_payslip_run_id = fields.Many2one('hr.payslip.run', 'Payslip Batch',
                                        help='Select the Payslip Batch for which you want do generate the Salary map Report')
    start_date = fields.Date('Start Date', default=time.strftime('%Y-%m-01'))
    end_date = fields.Date('End Date',
                           default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10])
    company_id = fields.Many2one("res.company", string="Company", required=True,
                                 default=lambda self: self.env.user.company_id.id)

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for res in self:
            if res.start_date > res.end_date:
                raise ValidationError('Start Date must be lower than End Date')

    def print_report(self):
        data = {'form': self.read(['slip_filter_by', 'hr_payslip_run_id', 'start_date', 'end_date'])[0]}
        return self.env.ref('l10n_ao_hr.action_report_salary').report_action(self, data=data)
