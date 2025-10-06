from odoo import api, fields, models


class EmployeeAppointment(models.Model):
    _name = 'ao.hr.employee.appointment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Appointment Sheet'

    name = fields.Char('Name')
    job_id = fields.Many2one(comodel_name='hr.job', string='Job position',tracking=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='Employee',tracking=True)
    department_id = fields.Many2one(comodel_name='hr.department', string='Department',tracking=True)
    appointed_by = fields.Many2one(comodel_name='hr.employee', string='Appointed by',tracking=True)
    department_manger_id = fields.Many2one(comodel_name='hr.employee', string='Department manager',tracking=True)
    motive = fields.Text('Motive')

    @api.onchange('employee_id')
    def change_employee_id(self):
        if self.employee_id:
            self.job_id = self.employee_id.job_id
            self.department_id = self.employee_id.department_id


