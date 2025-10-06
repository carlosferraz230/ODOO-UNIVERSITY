import time
from psycopg2 import sql
from datetime import datetime, timedelta, time
from datetime import time as datetime_time
from pytz import timezone
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
import calendar
from . import utils
import base64
from odoo.tools.safe_eval import safe_eval


class Payslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_leave_entry_lines(self, contract=None):
        leave_type = ['SF', 'ATRA', 'FJNR', 'FJR', 'FI']
        leave_data = []
        for type in leave_type:
            leave = self.env['hr.leave'].search(
                [('holiday_status_id.code', '=', type),
                 ('employee_id.contract_id', '=', contract.id), '&', ('state', '=', 'validate'),
                 ('payslip_state', '=', 'done')])
            if leave:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                attendance_line = {
                    'name': type,
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': sum([rec.number_of_days for rec in leave]),
                    'number_of_hours': sum([rec.number_of_hours_display for rec in leave]),
                    'amount': -1 * (sum([rec.number_of_hours_display for rec in leave]) * self.contract_id.wage_hour)
                }
                leave_data.append(attendance_line)
            print(leave_data)
        return leave_data

    def _get_worked_day_lines_values(self, domain=None):
        self.ensure_one()
        res = []
        hours_per_day = self._get_worked_day_lines_hours_per_day()
        work_hours = self.contract_id._get_work_hours(self.date_from, self.date_to, domain=domain)
        work_hours_ordered = sorted(work_hours.items(), key=lambda x: x[1])
        biggest_work = work_hours_ordered[-1][0] if work_hours_ordered else 0
        add_days_rounding = 0
        for work_entry_type_id, hours in work_hours_ordered:
            work_entry_type = self.env['hr.work.entry.type'].browse(work_entry_type_id)
            days = round(hours / hours_per_day, 5) if hours_per_day else 0
            if work_entry_type_id == biggest_work:
                days += add_days_rounding
            day_rounded = self._round_days(work_entry_type, days)
            add_days_rounding += (days - day_rounded)
            attendance_line = {
                'sequence': work_entry_type.sequence,
                'work_entry_type_id': work_entry_type_id,
                'number_of_days': day_rounded,
                'number_of_hours': hours,
            }
            res.append(attendance_line)
            print(res)
        return res

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """
        :returns: a list of dict containing the worked days values that should be applied for the given payslip
        """
        res = []
        # fill only if the contract as a working schedule linked
        self.ensure_one()
        contract = self.contract_id
        leave_lines = self._get_leave_entry_lines(contract)
        if contract.resource_calendar_id:
            res = self._get_worked_day_lines_values(domain=domain)
            if not check_out_of_contract:
                return res

            # If the contract doesn't cover the whole month, create
            # worked_days lines to adapt the wage accordingly
            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()
            if self.date_from < contract.date_start:
                start = fields.Datetime.to_datetime(self.date_from)
                stop = fields.Datetime.to_datetime(contract.date_start) + relativedelta(days=-1, hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False,
                                                                     domain=['|', ('work_entry_type_id', '=', False), (
                                                                         'work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)
                out_time = reference_calendar.get_work_duration_data(start, stop, compute_leaves=False,
                                                                     domain=['|', ('work_entry_type_id', '=', False), (
                                                                         'work_entry_type_id.is_leave', '=', False)])
                out_days += out_time['days']
                out_hours += out_time['hours']

            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract')
                res.append({
                    'sequence': work_entry_type.sequence,
                    'work_entry_type_id': work_entry_type.id,
                    'number_of_days': out_days,
                    'number_of_hours': out_hours,
                })
                res.extend(leave_lines)
            print(res)
        return res

    def compute_remuneration(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'BAS':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.remuneration = _sum
        return res

    def compute_overtimes(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'HEXTRA':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.overtimes = _sum
        return res

    def compute_extra_remunerations(self):
        for payslip in self:
            payslip.extra_remuneration = payslip.total_remunerations - payslip.remuneration - payslip.overtimes

    def compute_misses(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'FALTA':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.misses = _sum
        return res

    def compute_remuneration_inss_base(self):
        for slip in self:
            slip.remuneration_inss_base = slip.remuneration + slip.overtimes + slip.misses + slip.allowance

    def compute_remuneration_inss_extra(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code in ('ABOINSS', 'ABOINSSIRT'):
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.remuneration_inss_extra = _sum
        return res

    def _compute_allowances(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if not line.appears_on_payslip:
                    continue
                if line.category_id.code in ('ABO'):
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.allowance = _sum
        return res

    def compute_remuneration_inss_total(self):
        for slip in self:
            slip.remuneration_inss_total = slip.remuneration_inss_base + slip.remuneration_inss_extra

    def compute_amount_inss(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'INSS':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.amount_inss = _sum
        return res

    def compute_amount_irt(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.category_id.code == 'IRT':
                    _sum = line.total
            res[slip.id] = _sum
            slip.amount_irt = _sum
        return res

    def compute_extra_deductions(self):
        for payslip in self:
            _sum = 0.0
            for line in payslip.line_ids:
                if line.category_id.code in ['DED']:
                    _sum = _sum + line.deduction
            payslip.extra_deductions = -_sum
            # self.extra_deductions = self.total_deductions - self.misses - self.amount_inss - self.amount_irt

    def compute_amount_base_irt(self):
        res = {}
        for slip in self:
            _sum = 0.0
            _has_irt = False
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue;
                if line.category_id.code in (
                        'BAS', 'HEXTRA', 'FALTA', 'GRAT',):
                    _sum = _sum + line.total
                if line.category_id.code in ['IRT']:
                    _has_irt = True
            res[slip.id] = _sum
            ss_collect = ((_sum + slip.all_allowance()) * (3 / 100)) if _has_irt else 0.0

            if slip.struct_id.code in ["BASE", "CLASS_A"]:
                slip.amount_base_irt = _sum + slip.all_allowance() - ss_collect
            elif slip.struct_id.code in ["CLASS-B", "CLASS_B"]:
                slip.amount_base_irt = slip.total_remunerations - slip.misses
        return res

    def all_allowance(self):
        """
        07 - LEi 9.19 - Altera o Código do Imposto Sobre os Rendimentos de Trabalho e
        Revoga o Decreto que aprova a tabela de lucros minimos.
        :return: amount
        """
        amount = 0.0
        for res in self:
            for r in res.contract_id.remuneration_ids:
                if (r.rem_type != 'deduction') and (r.date_start <= res.date_to):
                    if not r.date_end or (r.date_end >= res.date_to):
                        if r.remunerationcode_id.code in ['sub_fer']:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount <= 30000:
                            continue
                        if r.remunerationcode_id.code in ['sub_ali', 'sub_trans'] and r.amount > 30000:
                            amount += (r.amount - 30000)
                            continue
                        if r.remunerationcode_id.code in ['sub_fam']:
                            unsent_amount = (5 / 100) * res.contract_id.wage
                            if r.amount > unsent_amount:
                                amount += (r.amount - unsent_amount)
                            continue
                        amount += r.amount
        return amount

    def _amount_irt_exempt(self):
        """Used in irt report"""
        amount = 0.0
        for res in self:
            for line in res.line_ids:
                if line.code in ['sub_ali', 'sub_trans'] and line.amount <= 30000:
                    amount += line.amount
                if line.code in ['sub_ali', 'sub_trans'] and line.amount > 30000:
                    amount += line.amount - (line.amount - 30000)
        return amount

    def compute_payslip_period(self):
        res = {}
        for slip in self:
            date_obj = datetime.strptime(str(slip.date_from), '%Y-%m-%d')
            months = {
                1: _('January'),
                2: _('February'),
                3: _('March'),
                4: _('April'),
                5: _('May'),
                6: _('June'),
                7: _('July'),
                8: _('August'),
                9: _('September'),
                10: _('October'),
                11: _('November'),
                12: _('December'),
            }
            # return months[int(date_obj.month)]
            slip.payslip_period = months[int(date_obj.month)]

    def compute_total_remunerations(self):
        res = {}
        for slip in self:
            rem_total = 0.0
            for slip_line in slip.line_ids:
                if slip_line.code not in ['GROSS', 'NET']:
                    if not slip_line.appears_on_payslip:
                        continue
                    rem_total += slip_line.remuneration
            res[slip.id] = rem_total
            slip.total_remunerations = rem_total
        return res

    def compute_total_deductions(self):
        ded_total = 0.0
        for slip in self:
            ded_total = 0.0
            for slipline in slip.line_ids:
                if slipline.code not in ['GROSS', 'NET']:
                    if not slipline.appears_on_payslip:
                        continue
                    if slipline.code != 'ss_collect':
                        if slipline.amount < 0:
                            ded_total += abs(slipline.amount)
            # res[slip.id] = ded_total
            slip.total_deductions = ded_total
        return ded_total

    def compute_total_paid(self):
        for slip in self:
            slip.total_paid = slip.total_remunerations - slip.total_deductions

    @api.depends('contract_id')
    def _compute_period_working_days(self):
        for payslip in self:
            # TODO Add code to consider public holidays
            total_days = 0.0
            if payslip.contract_id:
                for line in payslip.worked_days_line_ids:
                    if line.code == 'WORK100':
                        total_days += line.number_of_days
                payslip.period_working_days = total_days

    def compute_sub_ali(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code == 'sub_ali':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.sub_ali = _sum
        return res

    def compute_sub_fam(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code == 'sub_fam':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.sub_fam = _sum
        return res

    def compute_sub_trans(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code == 'sub_trans':
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.sub_trans = _sum
        return res

    def compute_total_sub_other(self):
        res = {}
        for slip in self:
            _sum = 0.0
            for line in slip.line_ids:
                if line.appears_on_payslip == False:
                    continue
                if line.code not in ['sub_ali', 'sub_trans', 'sub_fam', 'GROSS', 'NET'] \
                        and line.category_id.code in ['ABO', 'GRAT', 'HEXTRA', 'SOC']:
                    _sum = _sum + line.total
            res[slip.id] = _sum
            slip.total_sub_other = _sum
        return res

    sub_ali = fields.Float('Sub.Alim', digits=(10, 2), compute="compute_sub_ali")
    sub_trans = fields.Float('Sub.Trans', digits=(10, 2), compute="compute_sub_trans")
    sub_fam = fields.Float('Sub.Fam', digits=(10, 2), compute="compute_sub_fam")
    total_sub_other = fields.Float('Sub.Others', digits=(10, 2), compute="compute_total_sub_other")
    allowance = fields.Float(string="Allowances", digits=(10, 2), compute='_compute_allowances')
    remuneration = fields.Float(compute="compute_remuneration", digits=(10, 2), string='Remuneration',
                                help='This is the Wage amount')
    overtimes = fields.Float(compute="compute_overtimes", digits=(10, 2), string='Overtimes',
                             help='This is the total amount for Overtimes')
    extra_remunerations = fields.Float(compute="compute_extra_remunerations", digits=(10, 2),
                                       string='Extra Remuneration')
    misses = fields.Float(compute=compute_misses, digits=(10, 2), string='Misses',
                          help='This is the total discount for misses')
    remuneration_inss_base = fields.Float(compute="compute_remuneration_inss_base", digits=(10, 2),
                                          string='Base INSS',
                                          help='This is the INSS base amount')
    remuneration_inss_extra = fields.Float(compute="compute_remuneration_inss_extra", digits=(10, 2),
                                           string='Extra INSS Remuneration',
                                           help='Those are other INSS collectible remunerations')
    remuneration_inss_total = fields.Float(compute="compute_remuneration_inss_total", digits=(10, 2),
                                           string='Gross Remuneration')
    amount_inss = fields.Float(compute=compute_amount_inss, digits=(10, 2), string='INSS Amount')
    amount_irt = fields.Float(compute=compute_amount_irt, digits=(10, 2), string='IRT Amount')
    extra_deductions = fields.Float(compute="compute_extra_deductions", digits=(10, 2), string='Extra Deduction')
    amount_base_irt = fields.Float(compute="compute_amount_base_irt", digits=(10, 2), string='Base IRT')
    period_working_days = fields.Integer(compute='_compute_period_working_days', string='Payslip Days')
    payslip_period = fields.Char(compute=compute_payslip_period, string='Payslip Period')
    total_remunerations = fields.Float(compute="compute_total_remunerations", digits=(10, 2),
                                       string='Total of Remunerations')
    total_deductions = fields.Float(compute="compute_total_deductions", digits=(10, 2), string='Total of Deductions')
    total_paid = fields.Float(compute="compute_total_paid", digits=(10, 2), string='Total Paid')
    amount_ded = fields.Float(compute='_compute_amount_ded')

    # hasLeavesOrOvertime = fields.Boolean(compute=compute_hasLeavesOrOvertime, string='Exists Leaves or Overtime')
    # leave_ids = fields.One2many('hr.payslip.leaves', 'leave_id',string='Leaves',copy=True)

    def _compute_basic_net(self):
        for payslip in self:
            payslip.basic_wage = payslip._get_salary_line_total('BASE')
            payslip.net_wage = payslip.total_paid

    def compute_sheet(self):
        super(Payslip, self).compute_sheet()
        self.net_allowance()
        self.gross_allowance()

    def net_allowance(self):
        for res in self:
            for line in res.line_ids:
                if line.code in ['NET']:
                    line.amount = res.total_paid

    def gross_allowance(self):
        _CODE = ('IRT', 'INSS', 'INSSCOLLECT', 'NET', 'FALTA', 'DED')
        for res in self:
            for line in res.line_ids:
                if line.code in ['GROSS']:
                    line.amount = 0.0
                    line.amount = sum([item.amount for item in res.line_ids if item.category_id.code not in _CODE])

    def _compute_amount_ded(self):
        for res in self:
            _CODE = ('DES_ALI', 'DES_ADI')
            # _total = sum([line.total for line in res.details_by_salary_rule_category if line.code in _CODE]) * -1
            _total = 0
            res.amount_ded = _total

    def action_payslip_draft(self):
        for res in self:
            res.write({'state': 'draft'})

    def action_print_payslip(self):
        return self.env.ref('l10n_ao_hr.action_report_simple_payslip').report_action(self)


class PayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    company_id = fields.Many2one(comodel_name='res.company', string='Company', default=lambda l: l.env.user.company_id)
    structure_type_id = fields.Many2one('hr.payroll.structure.type', string="Salary Structure Type")
    budget = fields.Float(string="Budget", compute='_compute_total_payable')
    irt_amount_total = fields.Float(string="Total IRT", compute='_compute_total_payable')
    ss_amount_total = fields.Float(string="Total SS", compute='_compute_total_payable')

    salary_map_xls = fields.Binary('Salary Map XLS')

    def _compute_total_payable(self):
        for rec in self:
            rec.budget = sum([r.total_paid for r in rec.slip_ids])
            rec.irt_amount_total = sum([abs(r.amount_irt) for r in rec.slip_ids])
            rec.ss_amount_total = sum([abs(r.amount_inss) for r in rec.slip_ids])

    def action_send_email(self):
        # for res in self:
        #     for slip in res.slip_ids:
        #         template = self.env.ref('l10n_ao_hr.mail_template_payslipsendingtemplate')
        #         template.send_mail(slip.id)
        pass

    def recalculate_sheet(self):
        for slip in self.slip_ids:
            if slip.state in ['draft', 'verify']:
                slip.compute_sheet()

    def generate_salary_map_xls(self):
        salary_map_data = []
        payslips = self.env['hr.payslip'].search([('payslip_run_id', '=', self.id)])
        order_number = 0
        for slip in payslips:
            order_number += 1
            wage_and_allowance = slip.contract_id.wage + slip.allowance
            res = {
                'n': order_number,
                'name': slip.employee_id.name,
                'wage': slip.contract_id.wage,
                'departament': slip.contract_id.department_id.name,
                'job': slip.contract_id.job_id.name,
                'n_ss': slip.contract_id.fiscal_number,
                'desc_faltas': slip.contract_id.fiscal_number,
                'sub_ali': sum(line.total for line in slip.line_ids if line.code == 'sub_ali'),
                'sub_trans': sum(line.total for line in slip.line_ids if line.code == 'sub_trans'),
                'sub_fam': sum(line.total for line in slip.line_ids if line.code == 'sub_fam'),
                'sub_nat': sum(line.total for line in slip.line_ids if line.code == 'sub_nat'),
                'sub_ferias': sum(line.total for line in slip.line_ids if line.code == 'SF'),
                'total_sub': slip.allowance,
                'gross_salary': slip.total_remunerations,
                'ss_tax': sum(line.total for line in slip.line_ids if line.category_id.code == 'INSS') * -1,
                'rem_tribut': 0.0,
                'irt': sum(line.total for line in slip.line_ids if line.category_id.code == 'IRT') * -1,
                'salary_advance': sum(line.total for line in slip.line_ids if line.code == 'SAR'),
                'loan': sum(line.total for line in slip.line_ids if line.code == 'LO'),
                'fact_saude': 0.0,
                'outros_desc': 0.0,
                'total_deductions': slip.total_deductions,
                'percentage': ((slip.total_deductions / wage_and_allowance) / 100),
                'net_salary': slip.total_paid,
            }
            salary_map_data.append(res)
        return salary_map_data

    def print_salary_map_xlsx(self):
        salary_map = self.generate_salary_map_xls()
        utils.generate_xls(salary_map, self.name)
        self.salary_map_xls = base64.b64encode(utils.read_xls())


class PayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    def compute_remuneration(self):
        total = 0
        for slip_line in self:
            if slip_line.total >= 0:
                total = slip_line.total
            else:
                total = 0
            slip_line.remuneration = total
        return total

    def compute_deduction(self):
        total = 0
        for slip_line in self:
            if slip_line.total < 0:
                total = abs(slip_line.total)
            else:
                total = 0
            slip_line.deduction = total
        return total

    remuneration = fields.Float(compute=compute_remuneration, digits=(10, 2), string='Remuneration')
    deduction = fields.Float(compute=compute_deduction, digits=(10, 2), string='Deduction')

# class HrPayrollReport(models.Model):
#     _inherit = "hr.payroll.report"
#
#     def init(self):
#         super(HrPayrollReport, self).init()
#         query = """
#             SELECT
#                 p.id as id,
#                 CASE WHEN wd.id = min_id.min_line THEN 1 ELSE 0 END as count,
#                 CASE WHEN wet.is_leave THEN 0 ELSE wd.number_of_days END as count_work,
#                 CASE WHEN wet.is_leave THEN 0 ELSE wd.number_of_hours END as count_work_hours,
#                 CASE WHEN wet.is_leave and wd.amount <> 0 THEN wd.number_of_days ELSE 0 END as count_leave,
#                 CASE WHEN wet.is_leave and wd.amount = 0 THEN wd.number_of_days ELSE 0 END as count_leave_unpaid,
#                 CASE WHEN wet.is_unforeseen THEN wd.number_of_days ELSE 0 END as count_unforeseen_absence,
#                 CASE WHEN wet.is_leave THEN wd.amount ELSE 0 END as leave_basic_wage,
#                 p.name as name,
#                 p.date_from as date_from,
#                 p.date_to as date_to,
#                 e.id as employee_id,
#                 e.department_id as department_id,
#                 c.job_id as job_id,
#                 e.company_id as company_id,
#                 wet.id as work_code,
#                 CASE WHEN wet.is_leave IS NOT TRUE THEN '1' WHEN wd.amount = 0 THEN '3' ELSE '2' END as work_type,
#                 wd.number_of_days as number_of_days,
#                 wd.number_of_hours as number_of_hours,
#                 CASE WHEN wd.id = min_id.min_line THEN pln.total ELSE 0 END as net_wage,
#                 CASE WHEN wd.id = min_id.min_line THEN plb.total ELSE 0 END as basic_wage,
#                 CASE WHEN wd.id = min_id.min_line THEN plg.total ELSE 0 END as gross_wage
#             FROM
#                 (SELECT * FROM hr_payslip WHERE state IN ('done', 'paid')) p
#                     left join hr_employee e on (p.employee_id = e.id)
#                     left join hr_payslip_worked_days wd on (wd.payslip_id = p.id)
#                     left join hr_work_entry_type wet on (wet.id = wd.work_entry_type_id)
#                     left join (select payslip_id, min(id) as min_line from hr_payslip_worked_days group by payslip_id) min_id on (min_id.payslip_id = p.id)
#                     left join hr_payslip_line pln on (pln.slip_id = p.id and  pln.code = 'NET')
#                     left join hr_payslip_line plb on (plb.slip_id = p.id and plb.code = 'BASE')
#                     left join hr_payslip_line plg on (plg.slip_id = p.id and plg.code = 'GROSS')
#                     left join hr_contract c on (p.contract_id = c.id)
#             GROUP BY
#                 e.id,
#                 e.department_id,
#                 e.company_id,
#                 wd.id,
#                 wet.id,
#                 p.id,
#                 p.name,
#                 p.date_from,
#                 p.date_to,
#                 pln.total,
#                 plb.total,
#                 plg.total,
#                 min_id.min_line,
#                 c.id"""
#         tools.drop_view_if_exists(self.env.cr, self._table)
#         self.env.cr.execute(
#             sql.SQL("CREATE or REPLACE VIEW {} as ({})").format(sql.Identifier(self._table), sql.SQL(query)))
