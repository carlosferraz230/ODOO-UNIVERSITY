from odoo import http
from odoo.http import request


class GPSApi(http.Controller):

    @http.route(
        '/api/gps/update',
        type='json',
        auth='public',
        methods=['POST'],
        csrf=False
    )
    def update_location(self, **kwargs):

        vehicle_id = kwargs.get('vehicle_id')
        latitude = kwargs.get('latitude')
        longitude = kwargs.get('longitude')
        speed = kwargs.get('speed', 0)

        location = request.env[
            'fleet.vehicle.location'
        ].sudo().create({
            'vehicle_id': int(vehicle_id),
            'latitude': latitude,
            'longitude': longitude,
            'speed': speed,
        })

        return {
            'status': 'success',
            'id': location.id
        }