from odoo import fields, models, api , _
from odoo.exceptions import ValidationError


class Department(models.Model):
    _inherit = 'hr.department'

    def get_all_employee_list_per_department(self):
        return self.env['hr.employee'].search([('department_id','=',self.id)])

