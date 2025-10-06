from odoo import fields, models, api, _
from odoo.exceptions import Warning, UserError
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta

period_dict = {
    '0': _("Abertura"),
    '12': _("Normal"),
    '13': _("Regularizações"),
    '14': _("Apur. Resultados"),
    '15': _("Fecho")
}


class AccountFiscalYear(models.Model):
    _inherit = 'account.fiscal.year'
    _description = 'Account Fiscal Year'

    state = fields.Selection([('open', 'Open'), ('closed', 'Closed')], string="State", default="open")
    periods = fields.Many2many(comodel_name="account.fiscal.period", string="Period")
    clearance_move_id = fields.Many2one(comodel_name='account.move', string="Apur. Resultado")

    @api.model_create_multi
    def create(self, vals):
        result = super(AccountFiscalYear, self).create(vals)
        period = self._create_period(result)
        result.periods |= period
        return result

    def unlink(self):
        # for res in self:
        #     moves = self.env['account.move'].search([('year', '=', res.id)])
        #     if moves:
        #         raise Warning(_("Impossible to eliminate year with movements"))
        return super(AccountFiscalYear, self).unlink()

    # TODO: Descomentar quando o arquivo account_move.py for carregado
    # def write(self, vals):
    #     if "periods" in vals:
    #         periods_data = vals["periods"]
    #         new_period_ids = periods_data[0][2] if periods_data and periods_data[0][2] else []
    #
    #         for res in self:
    #             for period in res.periods:
    #                 if not new_period_ids or period.id not in new_period_ids:
    #                     moves = self.env['account.move'].search([('period', '=', period.id)], limit=1)
    #                     if moves:
    #                         raise UserError(_("Impossível eliminar um Período com lançamentos contábeis relacionados."))

    #    return super(AccountFiscalYear, self).write(vals)

    def _create_period(self, year_model):
        """
        normal entries of account move
        :param year_model:
        :return:
        """
        periods = self.env['account.fiscal.period']
        opening = self.env['account.fiscal.period'].create({
            'year': year_model.id,
            'start_date': year_model.date_from,
            'end_date': year_model.date_to,
            'period': '0',  # this is opening entries
            'company_id': year_model.company_id.id,
        })
        normal = self.env['account.fiscal.period'].create({
            'year': year_model.id,
            'start_date': year_model.date_from,
            'end_date': year_model.date_to,
            'period': '12',  # this is normal entries
            'company_id': year_model.company_id.id,
        })
        regularization = self.env['account.fiscal.period'].create({
            'year': year_model.id,
            'start_date': year_model.date_from,
            'end_date': year_model.date_to,
            'period': '13',  # this is regularization entries
            'company_id': year_model.company_id.id,
        })
        clearance = self.env['account.fiscal.period'].create({
            'year': year_model.id,
            'start_date': year_model.date_from,
            'end_date': year_model.date_to,
            'period': '14',  # this is clearance entries
            'company_id': year_model.company_id.id,
        })
        close = self.env['account.fiscal.period'].create({
            'year': year_model.id,
            'start_date': year_model.date_from,
            'end_date': year_model.date_to,
            'period': '15',  # this is close entries
            'company_id': year_model.company_id.id,
        })
        periods |= opening + normal + regularization + clearance + close
        return periods

    def button_close(self):
        self.state = 'closed'

    def clearance_result(self):
        if not self.clearance_move_id:
            clearance_result = self.env['clearance.wizard'].create({
                'year': self.id,
                'date_start': fields.Date.to_date(time.strftime('%Y-01-1')),
                'date_end': datetime.today().date() + relativedelta(months=+1, day=1, days=-1)
            })
            clearance_result.run_clearance()
        else:
            raise UserError("Este ano fiscal ja foi apurado\n"
                            "Consultar o lançamentos de diários")


class AccountFiscalPeriod(models.Model):
    _name = 'account.fiscal.period'
    _description = 'Fiscal Period'
    _order = 'period asc'

    name = fields.Char(string="Name", compute='_compute_name')
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    period = fields.Selection([
        ('0', _("Abertura")),
        ('12', _("Normal")),
        ('13', _("Regularizações")),
        ('14', _("Apur. Resultados")),
        ('15', _("Fecho"))
    ], string="Period")
    year = fields.Many2one(comodel_name='account.fiscal.year', string="Fiscal Year")
    company_id = fields.Many2one(comodel_name="res.company", default=lambda l: l.env.user.company_id,
                                 string="Company")

    def unlink(self):
        # for res in self:
        #     moves = self.env['account.move'].search([('period', '=', res.id)])
        #     if moves:
        #         raise Warning(_("Impossible to eliminate Period with movements"))
        return super(AccountFiscalPeriod, self).unlink()

    @api.depends('period')
    def _compute_name(self):
        for res in self:
            res.name = res.period + ' - ' + period_dict[res.period] if res.period else 'Novo'

    @api.constrains('start_date')
    def validate_date(self):
        if self.start_date > self.end_date:
            raise Warning(_("The start date cannot be greater than the end date"))


class Setup(models.TransientModel):
    _inherit = 'account.financial.year.op'

    year = fields.Many2one(related='company_id.accounting_year', required=1, readonly=False)

    @api.onchange('year')
    def onchange_year(self):
        if self.year:
            self.opening_date = self.year.date_from
            self.fiscalyear_last_day = self.year.date_to.day
            self.fiscalyear_last_month = str(self.year.date_to.month)
