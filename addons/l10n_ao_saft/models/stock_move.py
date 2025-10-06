from odoo import fields, models, api
from . import utils


class SAFTStockMove(models.Model):
    _inherit = 'stock.picking'

    def get_saft_data(self):
        result = {
            "MovementOfGoods": {
                "NumberOfMovementLines": 0,
                "TotalQuantityIssued": utils.gross_total(0.0),
                "StockMovement": [],
            }
        }

        _partner = ""
        st_pickings = self.filtered(
            lambda picking: picking.state in ['done', 'cancel'] and
                            picking.company_id == self.env.company
        )

        for number, st_picking in enumerate(st_pickings, start=1):
            status_code = 'A' if st_picking.state == 'cancel' else 'N'

            if st_picking.picking_type_code in ['incoming', 'outgoing']:
                _partner = st_picking.partner_id.id if st_picking.partner_id.vat else "CF"

            # Preencher endereço
            def get_address(picking):
                address = {}
                ship_from = ship_to = []

                if st_picking.picking_type_code in ['incoming', 'outgoing']:
                    partner = st_picking.partner_id
                    address = {
                        "BuildingNumber": "",
                        "StreetName": partner.street,
                        "AddressDetail": partner.contact_address,
                        "City": partner.city,
                        "PostalCode": partner.zip or "",
                        "Province": partner.state_id.name,
                        "Country": partner.country_id.code
                    }

                common_info = {
                    "DeliveryDate": fields.Date.to_string(st_picking.delivery_date),
                    "Address": address,
                }

                if st_picking.picking_type_code == "incoming":
                    ship_from = {
                        "DeliveryDate": fields.Date.to_string(st_picking.delivery_date),
                        "WarehouseID": st_picking.partne_id.name[:50],
                        "LocationID": st_picking.location_dest_id.complete_name[:30],
                        "Address": address,

                    }
                    ship_to = common_info

                elif st_picking.picking_type_code == "outgoing":
                    ship_from = {
                        "DeliveryDate": fields.Date.to_string(st_picking.delivery_date),
                        "WarehouseID": st_picking.company_id.name[:50],
                        "LocationID": st_picking.location_id.complete_name[:30],
                        "Address": address,

                    }
                    ship_to = common_info

                return {"ShipFrom": ship_from, "ShipTo": ship_to}

            stock_movement = {
                "DocumentNumber": st_picking.guide_sequence,  # f"GR 2022/{number}",
                "DocumentStatus": {
                    "MovementStatus": status_code,
                    "MovementStatusDate": st_picking.system_entry_date.isoformat(sep='T', timespec='seconds'),
                    "SourceID": st_picking.write_uid.id,
                    "SourceBilling": "P"
                },
                "Hash": st_picking.hash,
                "HashControl": st_picking.company_id.key_version or "0",
                "Period": fields.Date.to_string(st_picking.picking_date)[5:7],
                "MovementDate": fields.Date.to_string(st_picking.picking_date),
                "MovementType": st_picking.movement_type,
                "SystemEntryDate": st_picking.system_entry_date.isoformat(sep='T', timespec='seconds'),
                "CustomerID": _partner if st_picking.picking_type_code == "outgoing" else "",
                "SupplierID": _partner if st_picking.picking_type_code == "incoming" else "",
                "SourceID": st_picking.create_uid.id,
                "ShipTo": get_address(st_picking)["ShipTo"],
                "ShipFrom": get_address(st_picking)["ShipFrom"],
                "MovementStartTime": st_picking.date_done.isoformat(sep='T', timespec='seconds'),
                "Line": [{
                    "LineNumber": line.id,
                    "OrderReferences": {
                        "OriginatingON": st_picking.origin or "",
                        "OrderDate": fields.Date.to_string(st_picking.picking_date),
                    } if st_picking.origin else {},
                    "ProductCode": line.product_id.id,
                    "ProductDescription": line.product_id.name[:200],
                    "Quantity": line.quantity,
                    "UnitOfMeasure": line.product_uom.name or "Unidade(s)",
                    "UnitPrice": utils.gross_total(0.0),
                    "Description": line.product_id.name[:200],
                    "DebitAmount": utils.gross_total(0.0) if st_picking.picking_type_code == "incoming" else "",
                    "CreditAmount": utils.gross_total(0.0) if st_picking.picking_type_code == "outgoing" else "",
                } for line in st_picking.move_ids_without_package],
                "DocumentTotals": {
                    "TaxPayable":utils.gross_total(0.0),
                    "NetTotal": utils.gross_total(0.0),
                    "GrossTotal": utils.gross_total(0.0),
                }
            }
            result['MovementOfGoods']['StockMovement'].append(stock_movement)

        sp_to_process = st_pickings.filtered(lambda sp: sp.state == 'done')
        lines_process = sp_to_process.mapped('move_ids_without_package')
        total_qty_process = sum([line.quantity for line in lines_process])

        result['MovementOfGoods']['NumberOfMovementLines'] =len(lines_process)
        result['MovementOfGoods']['TotalQuantityIssued'] = utils.gross_total(total_qty_process)

        return result
