from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    guide_sequence = fields.Char(string="Guide Sequence")

    def do_print_picking(self):
        self.write({'printed': True})
        return self.env.ref('stock.action_report_delivery').report_action(self)

    def button_transport_slip(self):
        return self.env.ref('ht_stock_ao.action_report_transport_slip_ao').report_action(self)

    def button_validate(self):
        result = super(StockPicking, self).button_validate()
        sequence = self.env['ir.sequence'].next_by_code('stock.picking.ao') or '/'
        self.guide_sequence = sequence
        return result
