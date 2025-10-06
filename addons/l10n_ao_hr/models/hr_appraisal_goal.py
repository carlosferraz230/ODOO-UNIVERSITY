from odoo import fields, models, api, _
from odoo.exceptions import Warning


class HrAppraisalGoal(models.Model):
    _inherit = 'hr.appraisal.goal'

    manager_id = fields.Many2one('hr.employee', related='employee_id.parent_id', string="Employee Manager",
                                 required=True)
    state = fields.Selection(selection=[('new', 'New'), ('approved', 'Approved By Manager')], string='State',
                             default='new')
    description = fields.Text('Half year evaluation')
    year_end_description = fields.Text('Year-end evaluation')

    def button_manager_approved(self):
        if self.env.user.employee_id.id == self.manager_id.id:
            self.state = 'approved'
        else:
            raise Warning(_('Only Employee Manager can approve this gol!'))

    def action_confirm(self):
        if self.env.user.employee_id.id == self.manager_id.id:
            self.write({'progression': '100'})

        elif self.env.user.employee_id.id == self.employee_id.id:
            self.write({'progression': '100'})
        else:
            raise Warning(_('Only Employee or Manager mark as done the progression gol!'))

    def write(self, values):
        res = super(HrAppraisalGoal, self).write(values)
        if self.env.user.employee_id.id == self.manager_id.id:
            return res
        elif self.env.user.employee_id.id == self.employee_id.id:
            return res
        else:
            raise Warning(_('Only Employee or Manager can update this information!'))
