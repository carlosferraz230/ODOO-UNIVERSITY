from odoo import api, models, fields
from odoo.exceptions import ValidationError
from datetime import timedelta

class Driver(models.Model):
    _inherit = 'res.partner'

    vehicle_id = fields.Many2many(
        'fleet.vehicle',
        string="Veículo",
        compute="_compute_vehicle_id",
        inverse="_inverse_vehicle_id",
    )
    license = fields.Char(string="Carta de Condução")
    license_type = fields.Selection([
        ('heavy', 'Pesada'), ('amateur', 'Ligeiro Amador'), ('prof', 'Ligeiro Profissional')
    ], string="Tipo")
    start_date = fields.Date(string="Data de Emissão")
    end_date = fields.Date(string='Data de Expiração')

    # Campos relacionados a Expiração da Carta
    license_expired = fields.Boolean(
        string="Carta Expirada",
        compute="_compute_license_status",
    )

    license_expiring = fields.Boolean(
        string="Carta Próxima da Expiração",
        compute="_compute_license_status",
    )

    license_status = fields.Selection([
        ('valid', 'Válida'),
        ('expiring', 'Expira em Breve'),
        ('expired', 'Expirada'),
    ], compute="_compute_license_status",
        string="Estado da Carta")

    # Campos que devem ser Obrigatórios
    phone = fields.Char(required=True)
    function = fields.Char(required=True)
    vat = fields.Char(required=True)

    # Método que verifica a Expiração da Carta de Condução
    @api.depends('end_date')
    def _compute_license_status(self):
        today = fields.Date.today()

        for rec in self:

            rec.license_expired = False
            rec.license_expiring = False
            rec.license_status = 'valid'

            if rec.end_date:

                # EXPIRADA
                if rec.end_date < today:
                    rec.license_expired = True
                    rec.license_status = 'expired'

                # FALTAM 30 DIAS
                elif rec.end_date <= today + timedelta(days=31):
                    rec.license_expiring = True
                    rec.license_status = 'expiring'

    # Verificar se a Data de Criação da Carta não é Igual ou Maior que a Data de Expiração.
    @api.constrains('start_date', 'end_date')
    def _check_license_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date:
                if rec.start_date == rec.end_date:
                    raise ValidationError(
                        "A Data de Emissão da Carta de Condução não pode ser Igual à Data de Expiração."
                    )
                if rec.start_date > rec.end_date:
                    raise ValidationError(
                        "A Data de Emissão da Carta de Condução não pode ser Maior que a Data de Expiração."
                    )

    # Método que lança o Alerta que a Carta Expira dentro de 30 dias.
    def cron_check_driver_licenses(self):

        today = fields.Date.today()
        limit_date = today + timedelta(days=30)

        drivers = self.search([
            ('end_date', '!=', False)
        ])

        for driver in drivers:

            # CARTA EXPIRADA
            if driver.end_date < today:

                driver.message_post(
                    body="A Carta de Condução deste Motorista Expirou."
                )

            # FALTAM 30 DIAS
            elif driver.end_date <= limit_date:

                driver.message_post(
                    body=(
                        "A Carta de Condução deste Motorista "
                        "Expira em menos de 30 dias."
                    )
                )

    @api.depends()
    def _compute_vehicle_id(self):
        for driver in self:
            driver.vehicle_id = self.env['fleet.vehicle'].search([
                ('driver_id', '=', driver.id)
            ])

    def _inverse_vehicle_id(self):
        for driver in self:
            vehicles_to_assign = driver.vehicle_id.filtered(
                lambda vehicle: vehicle.driver_id != driver
            )
            vehicles_to_assign.write({'driver_id': driver.id})
