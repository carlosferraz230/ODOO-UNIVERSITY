from odoo import fields, models, api
import time
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import ValidationError


class ModelName(models.TransientModel):
    _name = 'wizard.indication'
    _description = 'Wizard indication of hr '

    start_date = fields.Datetime(string='Start Date')
    end_date = fields.Datetime(string='End Date'
                               )
    option = fields.Selection(
        [('all', 'Geral'), ('number_work_gender', 'Number Work By Degree Academic '),
         ('number_children', 'Number Dependents')],
        default='all')

    def get_costs_salary(self):
        salary_map_data = []
        costs_employee_start = self.env['hr.payslip.run'].search(
            [('date_start', '<=', self.start_date.strftime('%Y-%m-%d')),
             ('date_end', '>=', self.start_date.strftime('%Y-%m-%d')),
             ('structure_type_id.type', '=', 'employee')])
        costs_worker_start = self.env['hr.payslip.run'].search(
            [('date_start', '<=', self.start_date.strftime('%Y-%m-%d')),
             ('date_end', '>=', self.start_date.strftime('%Y-%m-%d')),
             ('structure_type_id.type', '=', 'worker')])
        costs_employee_end = self.env['hr.payslip.run'].search(
            [('date_start', '<=', self.end_date.strftime('%Y-%m-%d')),
             ('date_end', '>=', self.end_date.strftime('%Y-%m-%d')),
             ('structure_type_id.type', '=', 'employee')])
        costs_worker_end = self.env['hr.payslip.run'].search(
            [('date_start', '<=', self.end_date.strftime('%Y-%m-%d')),
             ('date_end', '>=', self.end_date.strftime('%Y-%m-%d')),
             ('structure_type_id.type', '=', 'worker')])

        payslips = self.env['hr.payslip'].search(
            [('payslip_run_id.name', '=', costs_employee_start[0].name if costs_employee_start else "")])
        payslips_end = self.env['hr.payslip'].search(
            [('payslip_run_id.name', '=', costs_employee_end[0].name if costs_employee_end else "")])
        res = {
            'sub_trans': sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'sub_trans']),
            'sub_trans_end': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_trans']),
            'sub_trans_vs': sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'sub_trans']) - sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_trans']),
            'sub_fam': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_fam']),
            'sub_fam_end': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_fam']),
            'sub_fam_vs': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_fam']) - sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_fam']),
            'sub_nat': sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'sub_nat']),
            'sub_nat_end': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_nat']),
            'sub_holiday_not_use': sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'sub_holiday_not_use']),
            'sub_holiday_not_use_end': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_holiday_not_use']),
            'sub_holiday_not_use_vs': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_holiday_not_use']) - sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'sub_holiday_not_use']),

            'sub_nat_vs': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_nat']) - sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'sub_nat']),
            'sub_ferias': sum([re.total for line in payslips for re in line.line_ids if re.code == 'SF']),
            'sub_ferias_end': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'SF']),
            'sub_ferias_vs': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'SF']) - sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'SF']),
            'total_sub': sum([line.allowance for line in payslips]),
            'total_sub_end': sum([line.allowance for line in payslips_end]),
            'total_sub_vs': sum([line.allowance for line in payslips_end]) - sum([line.allowance for line in payslips]),
            'gross_salary': sum([line.total_remunerations for line in payslips]),
            'gross_salary_end': sum([line.total_remunerations for line in payslips_end]),
            'gross_salary_vs': sum([line.total_remunerations for line in payslips_end]) - sum(
                [line.total_remunerations for line in payslips]),
            'ss_tax': costs_employee_start[0].ss_amount_total if costs_employee_start else 0.0,
            'ss_tax_end': costs_employee_end[0].ss_amount_total if costs_employee_end else 0.0,
            'ss_tax_vs': (costs_employee_start[0].ss_amount_total if costs_employee_start else 0.0) - (
                costs_employee_end[0].ss_amount_total if costs_employee_end else 0.0),
            'irt': costs_employee_start[0].irt_amount_total if costs_employee_start else 0.0,
            'irt_end': costs_employee_end[0].irt_amount_total if costs_employee_end else 0.0,
            'irt_vs': costs_employee_end[0].irt_amount_total if costs_employee_end else 0.0 - costs_employee_start[
                0].irt_amount_total if costs_employee_start else 0.0,
            'loan_end': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'LO']),
            'loan': sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'LO']),
            'loan_vs': sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'LO']) - sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'LO']),

            'misses': sum([re.total for line in payslips for re in line.line_ids if re.code == 'FALTA']),
            'misses_end': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'FALTA']),
            'misses_vs': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'FALTA']) - sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'FALTA']),
            'paid': costs_employee_start[0].budget if costs_employee_start else 0.0,
            'paid_end': costs_employee_end[0].budget if costs_employee_end else 0.0,
            'paid_vs': costs_employee_end[0].budget if costs_employee_end else 0.0 - costs_employee_start[
                0].budget if costs_employee_start else 0.0,
            'des_paid': (costs_employee_start[0].irt_amount_total if costs_employee_start else 0.0) + (
                costs_employee_start[
                    0].ss_amount_total if costs_employee_start else 0.0) + sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'FALTA']) + sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'LO']),
            'des_paid_end': (costs_employee_end[0].irt_amount_total if costs_employee_end else 0.0) + (
                costs_employee_end[
                    0].ss_amount_total if costs_employee_end else 0.0) + sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'FALTA']) + sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'LO']),
            'des_paid_vs': (costs_employee_end[0].irt_amount_total if costs_employee_end else 0.0) + (
                costs_employee_end[
                    0].ss_amount_total if costs_employee_end else 0.0) + sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'FALTA']) + sum(
                [re.total for line in payslips_end for re in line.line_ids if re.code == 'LO']) - (
                               costs_employee_start[0].irt_amount_total if costs_employee_start else 0.0) + (
                               costs_employee_start[
                                   0].ss_amount_total if costs_employee_start else 0.0) + sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'FALTA']) + sum(
                [re.total for line in payslips for re in line.line_ids if re.code == 'LO']),

            'budget': costs_worker_start[0].budget if costs_worker_start else 0.0,
            'budget_end': costs_worker_end[0].budget if costs_worker_end else 0.0,
            'budget_vs': costs_worker_end[0].budget if costs_worker_end else 0.0 - costs_worker_start[
                0].budget if costs_worker_start else 0.0,
            'des_budget': (costs_worker_start[0].irt_amount_total if costs_worker_start else 0.0) + (
                costs_worker_start[0].ss_amount_total if costs_worker_start else 0.0),
            'des_budget_end': (costs_worker_end[0].irt_amount_total if costs_worker_end else 0.0) + (
                costs_worker_end[0].ss_amount_total if costs_worker_end else 0.0),
            'des_budget_vs': (costs_worker_end[0].irt_amount_total if costs_worker_end else 0.0) + (
                costs_worker_end[0].ss_amount_total if costs_worker_end else 0.0) - (
                                 costs_worker_start[0].irt_amount_total if costs_worker_start else 0.0) + (
                                 costs_worker_start[0].ss_amount_total if costs_worker_start else 0.0)
            ,
            # 'total_deductions': total_deductions,
            # 'net_salary': net_salary,
            # 'sub_ali': sub_ali,
            # 'sub_ali_end': sum([re.total for line in payslips_end for re in line.line_ids if re.code == 'sub_ali']),
        }
        salary_map_data.append(res)

        return salary_map_data

    def all_work_location(self):
        location = self.env['hr.work.location'].search([])
        return location

    def all_departament(self):
        department = self.env['hr.department'].search([])
        return department

    def qty_number_department_start(self, department):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.start_date),

                                                        ('department_id', '=', department)
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('end_date', '<=', self.start_date),
                                                          ('department_id', '=', department)

                                                          ])
        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_male) + len(employee_female)}

    def qty_number_department_end(self, department):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '>=', self.start_date),
                                                        ('create_date', '<=', self.end_date),
                                                        ('department_id', '=', department)
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.end_date),
                                                          ('department_id', '=', department)

                                                          ])
        print(employee_female)
        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_male) + len(employee_female)}

    def qty_number_work_location_start(self, location):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.start_date),
                                                        ('work_location_id', '=', location)
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.start_date),
                                                          ('work_location_id', '=', location)

                                                          ])

        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_male) + len(employee_female)}

    def qty_number_age_start(self, location):
        if "Mais" in location:
            return {"male": 0, 'female': 0,
                    'total': 0}
        else:
            age1 = int(location[0:2])
            age2 = int(location[3:5])
            employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                            ('create_date', '<=', self.start_date),
                                                            ('age', '>=', age1),
                                                            ('age', '<=', age2)
                                                            ])
            employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                              ('create_date', '<=', self.start_date),
                                                              ('age', '>=', age1),
                                                              ('age', '<=', age2)

                                                              ])
            return {"male": len(employee_male), 'female': len(employee_female),
                    'total': len(employee_male) + len(employee_female)}

    def qty_number_age_end(self, location):
        if "Mais" in location:
            employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                            ('create_date', '<=', self.end_date),
                                                            ('age', '>=', 61),
                                                            ('age', '<=', 120)
                                                            ])
            employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                              ('create_date', '<=', self.end_date),
                                                              ('age', '>=', 61),
                                                              ('age', '<=', 120)

                                                              ])
            return {"male": len(employee_male), 'female': len(employee_female),
                    'total': len(employee_male) + len(employee_female)}
        else:
            age1 = int(location[0:2])
            age2 = int(location[3:5])
            employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                            ('create_date', '<=', self.end_date),
                                                            ('age', '>=', age1),
                                                            ('age', '<=', age2)
                                                            ])
            employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                              ('create_date', '<=', self.end_date),
                                                              ('age', '>=', age1),
                                                              ('age', '<=', age2)

                                                              ])
            return {"male": len(employee_male), 'female': len(employee_female),
                    'total': len(employee_male) + len(employee_female)}

    def qty_number_work_location_end(self, location):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.end_date),
                                                        ('work_location_id', '=', location)
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.end_date),
                                                          ('work_location_id', '=', location)

                                                          ])

        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_male) + len(employee_female)}

    @api.constrains('start_date', 'end_date')
    def check_dates(self):
        for res in self:
            if res.start_date > res.end_date:
                raise ValidationError(_('Start Date must be lower than End Date'))

    def qty_number_dependents_start(self, index):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.start_date),
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.start_date),
                                                          ])
        f = m = 0
        for rec in employee_female:
            if rec.fam_ids:
                if len(rec.fam_ids) == index:
                    f += 1
        for rec in employee_male:
            if rec.fam_ids:
                if len(rec.fam_ids) == index:
                    m += 1
        return {"male": m, 'female': f,
                'total': m + f}

    def qty_number_dependents_end(self, index):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.end_date),
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.end_date),
                                                          ])
        f = m = 0
        for rec in employee_female:
            if rec.fam_ids:
                if len(rec.fam_ids) == index:
                    f += 1
        for rec in employee_male:
            if rec.fam_ids:
                if len(rec.fam_ids) == index:
                    m += 1
        return {"male": m, 'female': f,
                'total': m + f}

    def qty_number_gender_employee_start(self):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.start_date),
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.start_date),
                                                          ])
        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_female) + len(employee_male)}

    def all_certificate(self):
        l = ['primary_school', 'graduate', 'high_school', 'pre_university', 'university_attendance', 'bachelor',
             'master', 'doctor',

             'licensed',
             'postgraduate',
             'postgraduate_professional_training',
             'phd', 'other']
        return l

    def qty_number_gender_employee_start_degree(self, certificate):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.start_date),
                                                        ('certificate', '=', certificate)
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.start_date),
                                                          ('certificate', '=', certificate)
                                                          ])
        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_female) + len(employee_male)}

    def qty_number_gender_employee_end_degree(self, certificate):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.end_date),
                                                        ('certificate', '=', certificate)
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.end_date),
                                                          ('certificate', '=', certificate)
                                                          ])
        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_female) + len(employee_male)}

    def qty_number_gender_employee_end(self):
        employee_male = self.env['hr.employee'].search([('gender', '=', 'male'),
                                                        ('create_date', '<=', self.end_date),
                                                        ('create_date', '>=', self.start_date),
                                                        ])
        employee_female = self.env['hr.employee'].search([('gender', '=', 'female'),
                                                          ('create_date', '<=', self.end_date),
                                                          ])
        return {"male": len(employee_male), 'female': len(employee_female),
                'total': len(employee_female) + len(employee_male)}

    def print_report(self):
        return self.env.ref("l10n_ao_hr.report_hr_indication_id").report_action(self)
