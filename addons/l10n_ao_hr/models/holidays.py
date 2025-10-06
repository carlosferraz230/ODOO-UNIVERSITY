from odoo import fields, models, api


class HolidaysStatus(models.Model):
    _inherit = 'hr.leave.type'

    code = fields.Char('Code', size=6, help='Type here a code for this Holiday Type')


class Holidays(models.Model):
    _inherit = 'hr.leave'
    sf_start = fields.Date('Date From')
    sf_end = fields.Date('Date To')
    leave_type_code = fields.Char('Type Code')
    disc_ali_trans = fields.Boolean(string="Discount on food and transport allowance ?", default=0)

    @api.onchange('date_from', 'date_to')
    def onchange_date_from_and_to(self):
        self.sf_end = self.date_to
        self.sf_start = self.date_from

    @api.onchange('holiday_status_id')
    def onchange_type_holidays(self):
        if self.holiday_status_id:
            self.leave_type_code = self.holiday_status_id.code
            self.disc_ali_trans = True if self.holiday_status_id.code == 'SF' else False

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        self.manager_id = self.employee_id and self.employee_id.parent_id
        self.department_id = self.employee_id.department_id
        self._compute_number_of_days()

        # # TODO enable in enterprise
        # self._onchange_date_from()
        # self._onchange_date_to()

    def action_approve(self):
        res = super(Holidays, self).action_approve()
        for leave in self:
            if leave.payslip_state != False and leave.holiday_status_id.code in ['SF']:
                remuneration = self.env['hr.remuneration.code'].search([('code', '=', 'sub_fer')])
                remuneration_line_fields = [(0, 0, {
                    'remunerationcode_id': remuneration.id,
                    'name': remuneration.name,
                    'date_start': leave.sf_start,
                    'date_end': leave.sf_end,
                    'rem_type': 'remuneration',
                    'amount': leave.employee_id.contract_id.wage / 2
                })]
                leave.employee_id.contract_id.remuneration_ids = remuneration_line_fields
        return res
