from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FleetService(models.Model):
    _name = 'fleet.service'
    _description = 'Serviço da Frota'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'service_date desc, id desc'

    name = fields.Char(string='Descrição', required=True)
    service_date = fields.Date(string='Data do Serviço', required=True, default=fields.Date.today)
    service_type = fields.Selection([
        ('travel', 'Viagem'),
        ('maintenance', 'Manutenção'),
        ('fuel', 'Abastecimento'),
        ('toll', 'Portagem'),
        ('fine', 'Multa'),
        ('other', 'Outro')
    ], string='Tipo de Serviço', required=True, tracking=True)

    vehicle_id = fields.Many2one('fleet.vehicle', string='Veículo', required=True)
    driver_id = fields.Many2one(
        'res.partner',
        string='Motorista',
        related='vehicle_id.driver_id',
        store=True,  # Opcional: armazena no banco para busca mais rápida
        readonly=True
    )
    # Campos de odómetro
    odometer_start = fields.Float(string='Odómetro Inicial (KM)', help='KM no início do serviço')
    odometer_end = fields.Float(string='Odómetro Final (KM)', help='KM no fim do serviço')
    distance_km = fields.Float(string='Distância (KM)', compute='_compute_distance', store=True)

    # Custos
    amount = fields.Monetary(string='Valor', required=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string='Moeda', default=lambda self: self.env.company.currency_id)
    amount_total = fields.Monetary(string='Valor Total', compute='_compute_amount_total', store=True,
                                   currency_field='currency_id')

    # Para manutenção
    maintenance_notes = fields.Text(string='Notas de Manutenção')
    next_maintenance_km = fields.Integer(string='Próxima Manutenção (KM)', compute='_compute_next_maintenance')

    # Estado
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('in_progress', 'Em Execução'),
        ('completed', 'Concluído'),
        ('cancelled', 'Cancelado')
    ], string='Estado', default='draft', tracking=True)

    # Faturação
    invoice_id = fields.Many2one('account.move', string='Fatura')

    @api.depends('odometer_start', 'odometer_end')
    def _compute_distance(self):
        for service in self:
            if service.odometer_start and service.odometer_end:
                service.distance_km = service.odometer_end - service.odometer_start
            else:
                service.distance_km = 0.0

    @api.depends('amount')
    def _compute_amount_total(self):
        for service in self:
            service.amount_total = service.amount

    @api.depends('service_type', 'odometer_end')
    def _compute_next_maintenance(self):
        for service in self:  # CORRIGIDO
            if service.service_type == 'maintenance' and service.odometer_end:
                service.next_maintenance_km = service.odometer_end + 10000
            else:
                service.next_maintenance_km = 0

    def action_start_service(self):
        """Iniciar serviço"""
        self.state = 'in_progress'

    def action_complete_service(self):
        """Concluir serviço"""
        self.state = 'completed'
        if self.odometer_end:
            self.vehicle_id.odometer = self.odometer_end

    def action_cancel_service(self):
        """Cancelar serviço"""
        self.state = 'cancelled'

    def action_create_invoice(self):
        """Criar fatura para o serviço"""
        self.ensure_one()

        # Diário de vendas
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

        if not journal:
            raise ValidationError(_('Nenhum diário de vendas encontrado.'))

        # Conta de receitas
        account = self.env['account.account'].search([
            ('company_id', '=', self.env.company.id),
            ('deprecated', '=', False),
            ('internal_group', '=', 'income'),
        ], limit=1)

        if not account:
            raise ValidationError(_('Nenhuma conta de receita encontrada.'))

        # Parceiro
        partner = self.driver_id or self.env.company.partner_id

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': partner.id,
            'journal_id': journal.id,
            'invoice_date': self.service_date,

            'invoice_line_ids': [(0, 0, {
                'name': self.name,
                'quantity': 1.0,
                'price_unit': self.amount,

                # MUITO IMPORTANTE
                'account_id': account.id,
            })],
        }

        #invoice = self.env['account.move'].create(invoice_vals)

       # self.invoice_id = invoice.id

        return {
            'type': 'ir.actions.act_window',
            'name': 'Fatura',
            'res_model': 'account.move',
           # 'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }

    @api.constrains('odometer_start', 'odometer_end')
    def _check_odometer(self):
        for service in self:
            if service.odometer_start and service.odometer_end and service.odometer_end < service.odometer_start:
                raise ValidationError(_('Odómetro final deve ser superior ao inicial!'))

    # Acção que cuida do Relatório PDF
    def action_print_report(self):
        """Ação para imprimir o relatório do serviço em PDF"""
        return self.env.ref('fleetprd.report_fleet_service').report_action(self)
