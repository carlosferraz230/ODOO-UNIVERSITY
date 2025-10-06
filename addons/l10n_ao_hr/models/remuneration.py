from datetime import datetime
from odoo import models, fields, api
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from dateutil import relativedelta


class RemunerationCode(models.Model):
    _name = 'hr.remuneration.code'
    _description = 'Remuneration Code'
    _order = 'name'

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    type = fields.Selection([('remuneration', 'Remuneration'), ('deduction', 'Deduction')], 'Type', required=True)
    remuneration_ids = fields.One2many('hr.remuneration', 'remunerationcode_id', string='Remunerations in this code')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)


class Remuneration(models.Model):
    _name = 'hr.remuneration'
    _description = 'Remuneration'
    _order = 'rem_type'

    name = fields.Char('Description')
    date_start = fields.Date('Start Date', required=True, default=datetime.strftime(datetime.now(), '%Y-%m-01'))
    date_end = fields.Date('End Date')
    amount = fields.Float('Amount', digits=(10, 2), required='True')
    remunerationcode_id = fields.Many2one('hr.remuneration.code', string='Remuneration Code', required=True,
                                          help='Select the remuneration code for the remuneration')
    contract_id = fields.Many2one('hr.contract', string='Contract', required='True', ondelete='cascade')
    rem_type = fields.Selection([('remuneration', 'Remuneration'), ('deduction', 'Deduction')], 'Type')
    rem_day = fields.Float(string="Amount Day", compute="_compute_rem_days")
    rem_hour = fields.Float(string="Amount Hour", compute="_compute_rem_hours")

    @api.onchange('remunerationcode_id')
    def onchange_remuneration_code_id(self):
        default = str(datetime.now() + relativedelta.relativedelta(months=+1, day=16, days=-1))[:10]
        if self.remunerationcode_id:
            self.rem_type = self.remunerationcode_id.type
            self.name = self.remunerationcode_id.name
            if self.remunerationcode_id.code == 'sub_dec_terceiro' and self.contract_id.date_start and self.contract_id.date_end:
                if self.contract_id.date_start.year == self.contract_id.date_end.year:
                    print(self.contract_id.date_end)
                    print(self.contract_id.date_start)
                    self.amount = (int(self.contract_id.date_end.month) - int(
                        self.contract_id.date_start.month)) * self.contract_id.wage / 12
                elif int(self.contract_id.date_end.year) >= int(datetime.now().strftime('%d-01-%Y')[6:]):

                    self.amount = (int(datetime.now().strftime('%d-%m-%Y')[3:5]) - int(
                        datetime.now().strftime('%d-01-%Y')[
                        3:5])) * self.contract_id.wage / 12

    def _compute_rem_hours(self):
        for res in self:
            _week_hours = res.contract_id.resource_calendar_id.hours_per_week
            res.rem_hour = round((res.amount * 12) / (_week_hours * 52), 2)

    def _compute_rem_days(self):
        for res in self:
            if res.contract_id.resource_calendar_id:
                resource = res.contract_id.resource_calendar_id
                _rem_day = res.rem_hour * resource.hours_per_day
                res.rem_day = _rem_day

    @api.model
    def create(self, values):
        remuneration_code_id = values['remunerationcode_id']
        remuneration_code = self.env['hr.remuneration.code'].browse([remuneration_code_id])
        values['amount'] = abs(values['amount'])
        values['rem_type'] = remuneration_code.type
        return super(Remuneration, self).create(values)

    def write(self, values):
        if 'remunerationcode_id' in values:
            remuneration_code_id = values['remunerationcode_id']
            remuneration_code = self.env['hr.remuneration.code'].browse([remuneration_code_id])
            values['rem_type'] = remuneration_code.type
        if 'amount' in values:
            values['amount'] = abs(values['amount'])
        return super(Remuneration, self).write(values)
