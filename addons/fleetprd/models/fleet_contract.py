from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta, datetime


class FleetContract(models.Model):
    _name = 'fleet.contract'
    _description = 'Contrato de Frota'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_start desc'

    name = fields.Char(
        string='Referência do Contrato',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('Novo')
    )
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Veículo',
        required=True,
        tracking=True
    )
    contract_type = fields.Selection([
        ('leasing', 'Leasing'),
        ('rental', 'Aluguer'),
        ('insurance', 'Seguro'),
        ('maintenance', 'Manutenção'),
        ('other', 'Outro')
    ], string='Tipo de Contrato', required=True, tracking=True)

    provider_id = fields.Many2one(
        'res.partner',
        string='Fornecedor',
        required=True,

    )
    # ADICIONE ESTE CAMPO PARA MOSTRAR O MOTORISTA
    driver_id = fields.Many2one(
        'res.partner',
        string='Motorista',
        related='vehicle_id.driver_id',
        store=True,  # Opcional: armazena no banco para busca mais rápida
        readonly=True
    )

    date_start = fields.Date(string='Data de Início', required=True, tracking=True)
    date_end = fields.Date(string='Data de Fim', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('active', 'Ativo'),
        ('expired', 'Expirado'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)

    monthly_cost = fields.Monetary(
        string='Custo Mensal',
        currency_field='currency_id',
        required=True
    )
    total_contract_value = fields.Monetary(
        string='Valor Total do Contrato',
        compute='_compute_total_value',
        store=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Moeda',
        default=lambda self: self.env.company.currency_id
    )

    notes = fields.Text(string='Observações')

    # Campos que cuidam da Segurança
    user_id = fields.Many2one('res.users', string="Responsável", default=lambda self: self.env.user)
    # Adicione este campo
    is_public = fields.Boolean(string="Público", default=False)

    @api.model
    def create(self, vals):
        if vals.get('name', _('Novo')) == _('Novo'):
            vals['name'] = self.env['ir.sequence'].next_by_code('fleet.contract') or _('Novo')
        return super(FleetContract, self).create(vals)

    @api.depends('monthly_cost', 'date_start', 'date_end')
    def _compute_total_value(self):
        for contract in self:
            if contract.date_start and contract.date_end:
                months = (contract.date_end.year - contract.date_start.year) * 12 + \
                         (contract.date_end.month - contract.date_start.month)
                contract.total_contract_value = contract.monthly_cost * max(months, 1)
            else:
                contract.total_contract_value = 0.0

    def action_activate(self):
        self.state = 'active'

    def action_expire(self):
        self.state = 'expired'

    def action_cancel(self):
        self.state = 'cancelled'

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for contract in self:
            if contract.date_start >= contract.date_end:
                raise ValidationError(_('A data de início deve ser anterior à data de fim!'))

    @api.model
    def cron_check_expiring_contracts(self):
        """Verificar contratos a expirar (para agendamento automático)"""
        today = fields.Date.today()
        expiring_date = today + timedelta(days=30)

        expiring_contracts = self.search([
            ('state', '=', 'active'),
            ('date_end', '<=', expiring_date),
            ('date_end', '>=', today)
        ])

        for contract in expiring_contracts:
            contract.message_post(
                body=_('O contrato %s expira em %s dias!') % (
                    contract.name,
                    (contract.date_end - today).days
                ),
                subject=_('Alerta: Contrato a Expirar'),
                partner_ids=[contract.vehicle_id.driver_id.partner_id.id] if contract.vehicle_id.driver_id else []
            )

    def action_print_report(self):
        """Ação para imprimir o relatório do contrato"""
        return self.env.ref('fleetprd.report_fleet_contract').report_action(self)
