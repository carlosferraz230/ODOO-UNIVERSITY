# -*- coding: utf-8 -*-
# Part of Creyox Technologies

from odoo import fields, models, Command
from odoo.exceptions import ValidationError


class AccountMoveInherit(models.Model):
    _inherit = 'account.move'

    stock_picking_count = fields.Integer(
        string="Total Stock Pickings",
        compute="compute_stock_picking_count",
        default=0
    )

    stock_move_count = fields.Integer(
        string="Total Stock Move",
        compute='compute_stock_move_count',
        default=0
    )

    def action_post(self):
        res = super(AccountMoveInherit, self).action_post()

        for record in self:

            # Processar apenas facturas / vendas
            if record.move_type not in ['out_invoice', 'in_invoice']:
                continue

            if not record.env.company.invoice:
                continue

            move_or_picking = record.env.company.create_stock_move_or_picking
            warehouse = record.company_id.warehouse_id

            if not warehouse:
                continue

            # Definir localização
            if record.move_type == 'out_invoice':
                picking_type = warehouse.out_type_id.id
                location_id = warehouse.lot_stock_id.id
                location_dest_id = record.partner_id.property_stock_customer.id

            elif record.move_type == 'in_invoice':
                picking_type = warehouse.in_type_id.id
                location_id = record.partner_id.property_stock_supplier.id
                location_dest_id = warehouse.lot_stock_id.id

            # Criar Transferência de Stock
            if move_or_picking == 'create_stock_picking_from_invoice':
                stock_move_data = []

                for line in record.invoice_line_ids:

                    if not line.product_id or line.product_id.type != 'product':
                        continue

                    stock_move_data.append(Command.create({
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                        'name': line.product_id.name,
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                    }))

                if not stock_move_data:
                    continue

                picking = record.env['stock.picking'].create({
                    'partner_id': record.partner_id.id,
                    'location_id': location_id,
                    'location_dest_id': location_dest_id,
                    'picking_type_id': picking_type,
                    'move_type': 'direct',
                    'scheduled_date': record.invoice_date,
                    'move_lines': stock_move_data,
                    'account_move_id': record.id
                })

                # Confirmar Transferência
                picking.action_confirm()

                # Set done quantities
                for move in picking.move_ids_without_package:
                    for move_line in move.move_line_ids:
                        move_line.qty_done = move.product_uom_qty

                # Validar Transferência Automaticamente
                picking.button_validate()

            # Criar Movimento de Stock Automaticamente
            elif move_or_picking == 'create_stock_moves_from_invoice':
                for line in record.invoice_line_ids:

                    if not line.product_id or line.product_id.type != 'product':
                        continue

                    record.env['stock.move'].create({
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.quantity,
                        'product_uom': line.product_uom_id.id,
                        'name': line.product_id.name,
                        'location_id': location_id,
                        'location_dest_id': location_dest_id,
                        'account_move_line_id': line.id,
                    })

        return res

    def compute_stock_picking_count(self):
        for invoice in self:
            invoice.stock_picking_count = self.env['stock.picking'].search_count([
                ('account_move_id', '=', invoice.id)
            ])

    def compute_stock_move_count(self):
        for invoice in self:
            line_ids = invoice.invoice_line_ids.mapped('id')
            invoice.stock_move_count = self.env['stock.move'].search_count([
                ('account_move_line_id', 'in', line_ids)
            ])

    def action_show_stock_picking(self):
        self.ensure_one()
        stock_pickings = self.env['stock.picking'].search([
            ('account_move_id', '=', self.id)
        ])

        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')

        if len(stock_pickings) > 1:
            action['domain'] = [('id', 'in', stock_pickings.ids)]

        elif len(stock_pickings) == 1:
            action['views'] = [(self.env.ref('stock.view_picking_form').id, 'form')]
            action['res_id'] = stock_pickings.id

        else:
            raise ValidationError("System couldn't find Delivery Order !!")

        return action

    def action_show_stock_move(self):
        self.ensure_one()
        line_ids = self.invoice_line_ids.mapped('id')

        stock_moves = self.env['stock.move'].search([
            ('account_move_line_id', 'in', line_ids)
        ])

        action = self.env['ir.actions.act_window']._for_xml_id('stock.stock_move_action')

        if len(stock_moves) > 1:
            action['domain'] = [('id', 'in', stock_moves.ids)]

        elif len(stock_moves) == 1:
            action['views'] = [(self.env.ref('stock.view_move_form').id, 'form')]
            action['res_id'] = stock_moves.id

        else:
            raise ValidationError("System couldn't find Stock Moves !!")

        return action
