from odoo import models, fields, api


class FleetVehicleLocation(models.Model):
    _name = 'fleet.vehicle.location'
    _description = 'Fleet Vehicle Location'
    _rec_name = 'vehicle_id'
    _order = 'gps_time desc'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Veículo',
        required=True
    )

    driver_id = fields.Many2one(
        'res.partner',
        string='Motorista'
    )

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):

        for rec in self:

            if rec.vehicle_id:

                rec.driver_id = rec.vehicle_id.driver_id.id

            else:

                rec.driver_id = False

    latitude = fields.Float(
        string="Latitude",
        required=True
    )

    longitude = fields.Float(
        string="Longitude",
        required=True
    )

    speed = fields.Float(
        string="Velocidade"
    )

    gps_time = fields.Datetime(
        string='GPS Time',
        default=fields.Datetime.now
    )

    date = fields.Datetime(
        default=fields.Datetime.now
    )

    address = fields.Text()

    map_html = fields.Html(
        string="Mapa",
        compute="_compute_map_html",
        sanitize=False
    )

