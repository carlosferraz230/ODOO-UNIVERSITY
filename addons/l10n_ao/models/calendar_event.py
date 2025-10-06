from odoo import models, fields


class HolidayCalendarEvent(models.Model):
    _inherit = 'calendar.event'

    is_public_holiday = fields.Boolean("Is Public Holiday")

