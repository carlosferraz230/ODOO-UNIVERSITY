from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


# =========================================================
# VEÍCULO
# =========================================================
class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    # Campos que devem ser Obrigatórios no odoo, para um Melhor trabalho
    manager_id = fields.Many2one(required=True)
    brand_id = fields.Many2one(required=True)
    service_id = fields.Many2one()
    vin_sn = fields.Char(required=True)
    driver_id = fields.Many2one('res.partner', string="Motorista", required=True)
    car_value = fields.Float(required=True)
    license_plate = fields.Char(required=True)
    # Terminou aqui

    # Campos que estejam em fleet.vehicle.model, agora tem que estar em fleet.fleet
    seats = fields.Integer(string="Número de Lugares", required=True)
    doors = fields.Integer(string="Número de Portas", required=True)
    color = fields.Selection([
        ('red', 'Vermelho'), ('white', 'Branco'), ('black', 'Preto'), ('green', 'Verde'),
        ('pink', 'Rosa'), ('orange', 'Laranja'), ('yellow', 'Amarelo'), ('brown', 'Castanho'),
        ('blue', 'Azul'), ('cream', 'Creme')
    ], string="Cor", required=True)
    model_year = fields.Char(string="Ano do Modelo", required=True)
    #trailer_hook = fields.Boolean(string="Trailer Hook")
    #electric_assistance = fields.Boolean(string="Assistência Electrica")
    # ENGINE INFORMATION
    default_fuel_type = fields.Selection([
        ('diesel', 'Diesel'),
        ('gasoline', 'Gasoline'),
        ('hybrid', 'Hybrid'),
        ('electric', 'Electric'),
    ], string="Tipo de Combustível")

    default_co2 = fields.Float(string="Emissão de CO2")
    co2_standard = fields.Char(string="CO2 Padrão")

    transmission = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automático'),
    ], string="Transmissão")

    power = fields.Float(string="Power (kW)")
    horsepower = fields.Integer(string="Horsepower")
    horsepower_tax = fields.Float(string="Horsepower Tax (Kz)")
    # Terminou aqui

    # VENDORS
    vendors = fields.Many2many(
        'res.partner',
        string="Fornecedor"
    )
    # Terminou aqui

    contract_ids = fields.One2many(
        'fleet.contract',
        'vehicle_id',
        string='Contratos')

    current_contract_id = fields.Many2one(
        'fleet.contract',
        string='Contrato Ativo',
        compute='_compute_current_contract',
        store=True)

    service_ids = fields.One2many(
        'fleet.service',
        'vehicle_id',
        string='Serviços')

    total_service_cost = fields.Monetary(
        string='Custo Total de Serviços',
        compute='_compute_service_costs',
        store=True,
        currency_field='currency_id')

    last_service_date = fields.Date(
        string='Último Serviço',
        compute='_compute_service_dates',
        store=True)

    next_service_km = fields.Integer(
        string='Próxima Manutenção (KM)',
        compute='_compute_next_service_km',
        store=True)

    total_km_traveled = fields.Float(
        string='Total KM Percorridos',
        compute='_compute_total_km',
        store=True)

    cost_per_km = fields.Float(
        string='Custo por KM',
        compute='_compute_cost_per_km',
        store=True)

    efficiency_rating = fields.Selection([
        ('excellent', 'Excelente'),
        ('good', 'Bom'),
        ('average', 'Médio'),
        ('poor', 'Ruim')],
        string='Avaliação de Eficiência',
        compute='_compute_efficiency',
        store=True)

    color_state = fields.Selection([
        ('green', 'EM SERVIÇO'),
        ('blue', 'DISPONÍVEL'),
        ('red', 'MANUTENÇÃO'),
        ('orange', 'SEM ESTADO')
    ], compute="_compute_color_state", store=True, string="Estado")

    # DEFINIR ESTADO DEFAULT
    def _default_state_id(self):
        state = self.env['fleet.vehicle.state'].search(
            [('name', 'ilike', 'Dispon')], limit=1)
        return state.id if state else False

    @api.depends('state_id')
    def _compute_color_state(self):
        for rec in self:
            name = rec.state_id.name.lower() if rec.state_id else ''
            if 'dispon' in name:
                rec.color_state = 'blue'
            elif 'servi' in name or 'uso' in name:
                rec.color_state = 'green'
            elif 'manut' in name:
                rec.color_state = 'red'
            elif 'sem' in name or 'estado' in name:
                rec.color_state = 'orange'
            else:
                rec.color_state = False

    @api.depends('service_ids.amount_total')
    def _compute_service_costs(self):
        for vehicle in self:
            vehicle.total_service_cost = sum(
                vehicle.service_ids.mapped('amount_total')
            )

    @api.depends('service_ids.service_date')
    def _compute_service_dates(self):
        for vehicle in self:
            services = vehicle.service_ids.filtered(
                lambda s: s.service_type == 'maintenance'
            )

            if services:
                vehicle.last_service_date = max(
                    services.mapped('service_date')
                )
            else:
                vehicle.last_service_date = False

    @api.depends('service_ids.odometer_end')
    def _compute_next_service_km(self):
        for vehicle in self:

            maintenance_services = vehicle.service_ids.filtered(
                lambda s:
                s.service_type == 'maintenance'
                and s.odometer_end
            )

            if maintenance_services:

                last_maintenance = max(
                    maintenance_services,
                    key=lambda s: s.odometer_end
                )

                vehicle.next_service_km = (
                        last_maintenance.odometer_end + 10000
                )

            else:
                current_odometer = vehicle.odometer or 0
                vehicle.next_service_km = current_odometer + 5000

    @api.depends('service_ids.odometer_start', 'service_ids.odometer_end')
    def _compute_total_km(self):
        for vehicle in self:
            services_with_km = vehicle.service_ids.filtered(
                lambda s:
                s.odometer_start
                and s.odometer_end
                and s.odometer_end >= s.odometer_start
            )

            vehicle.total_km_traveled = sum(
                (
                        s.odometer_end - s.odometer_start
                )
                for s in services_with_km
            )

    @api.depends(
        'total_service_cost',
        'total_km_traveled'
    )
    def _compute_cost_per_km(self):
        for vehicle in self:

            if vehicle.total_km_traveled > 0:

                vehicle.cost_per_km = (
                        vehicle.total_service_cost /
                        vehicle.total_km_traveled
                )

            else:
                vehicle.cost_per_km = 0.0

    @api.depends('cost_per_km')
    def _compute_efficiency(self):
        for vehicle in self:

            if vehicle.cost_per_km <= 10:
                vehicle.efficiency_rating = 'excellent'

            elif vehicle.cost_per_km <= 20:
                vehicle.efficiency_rating = 'good'

            elif vehicle.cost_per_km <= 40:
                vehicle.efficiency_rating = 'average'

            else:
                vehicle.efficiency_rating = 'poor'

    # =========================================================
    # COMPUTES
    # =========================================================
    @api.depends('contract_ids.state', 'contract_ids.date_end')
    def _compute_current_contract(self):
        today = fields.Date.today()
        for vehicle in self:
            active_contract = vehicle.contract_ids.filtered(lambda c: c.state == 'active'
                                                                      and c.date_end and c.date_end >= today)
            vehicle.current_contract_id = active_contract[:1] if active_contract else False

    # =========================================================
    # ONCHANGE
    # =========================================================
    @api.onchange('brand_id')
    def _onchange_brand_id(self):
        if self.brand_id:
            return {
                'domain': {
                    'model_id': [
                        ('brand_id', '=', self.brand_id.id)
                    ]
                }
            }

        return {
            'domain': {
                'model_id': []
            }
        }

    # =========================================================
    # ACTIONS
    # =========================================================
    def action_request_maintenance(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': _('Solicitar Manutenção'),
            'res_model': 'fleet.service',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicle_id': self.id,
                'default_service_type': 'maintenance',
                'default_odometer_start': self.odometer,
                'default_name': _('Manutenção Preventiva - %s') % self.name,
            }
        }

    # Metódo que trata da Impressão do Relatório PDF
    def action_print_report(self):
        """Action to print vehicle report in PDF"""
        return self.env.ref('fleetprd.report_fleet_vehicle').report_action(self)

    # Trabalhar
    service_count = fields.Integer(
        compute='_compute_service_count'
    )

    contract_count = fields.Integer(
        compute='_compute_contract_count'
    )

    # ---------------------------------------------------------
    # CONTADORES
    # ---------------------------------------------------------

    def _compute_service_count(self):
        for rec in self:
            rec.service_count = self.env[
                'fleet.service'
            ].search_count([
                ('vehicle_id', '=', rec.id)
            ])

    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = self.env[
                'fleet.contract'
            ].search_count([
                ('vehicle_id', '=', rec.id)
            ])

    # ---------------------------------------------------------
    # ACTION SERVIÇOS
    # ---------------------------------------------------------

    def action_open_services(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Novo Serviço',
            'res_model': 'fleet.service',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicle_id': self.id,
                'default_driver_id': self.driver_id.id,
            }
        }

    # ---------------------------------------------------------
    # ACTION CONTRATOS
    # ---------------------------------------------------------

    def action_open_contracts(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Novo Contrato',
            'res_model': 'fleet.contract',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_vehicle_id': self.id,
                'default_driver_id': self.driver_id.id,
            }
        }

    # Método que verifica se a Carta de Conduçõ do Motorista está exprirada ou não.
    @api.constrains('driver_id')
    def _check_driver_license(self):

        for rec in self:

            if rec.driver_id and rec.driver_id.license_expired:
                raise ValidationError(
                    "Não é possível atribuir este Veículo.\n\n"
                    "A Carta de Condução do Motorista está Expirada."
                )

