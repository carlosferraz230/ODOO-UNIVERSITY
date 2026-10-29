from odoo import api, models, fields, api, _
from odoo.exceptions import ValidationError
from . import utils
from datetime import datetime


class SAFTSaleOrder(models.Model):
    _inherit = 'sale.order'

    def _check_sale_required_fields(self):
        for order in self:
            if not order.date_order:
                raise ValidationError(_('Por favor, adicione uma Data à venda.'))
            if not order.partner_id:
                raise ValidationError(_('Por favor, adicione um Cliente.'))
            lines = order.order_line.filtered(lambda line: not line.display_type)
            if not lines:
                raise ValidationError(_('Por favor, adicione um Produto'))
            if any(not line.product_id for line in lines):
                raise ValidationError(_('Por favor, adicione um Produto'))
            if any(not line.tax_id for line in lines):
                raise ValidationError(_('Por favor, adicione IVA'))

    def action_confirm(self):
        self._check_sale_required_fields()
        return super().action_confirm()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if 'partner_id' in fields_list and not self.env.context.get('default_partner_id'):
            values['partner_id'] = self.env['res.partner'].get_final_consumer(
                values.get('company_id') or self.env.company.id
            ).id
        return values

    @api.model
    def create(self, vals):
        if not vals.get('partner_id') and not self.env.context.get('default_partner_id'):
            vals['partner_id'] = self.env['res.partner'].get_final_consumer(
                vals.get('company_id') or self.env.company.id
            ).id
        return super().create(vals)

    def get_saft_data(self):
        result = {
            "WorkingDocuments": {
                "NumberOfEntries": 0,
                "TotalDebit": 0,
                "TotalCredit": 0,
                "WorkDocument": [],
            },
        }

        sales = self.filtered(
            lambda sale: sale.state in ['draft','sent','sale'] and
                        sale.type in ['PP', 'OR', 'OU'] and
                        sale.company_id == self.env.company
        )

        for sale in sales:
            status_code = {'cancel': 'A', 'sale': 'F'}.get(sale.state, 'N')
            sale_order = self._generate_sale_order(sale, status_code)

            for line in sale.order_line:
                line_data = self._generate_line_data(line, sale)
                sale_order["Line"].append(line_data)

            result["WorkingDocuments"]["WorkDocument"].append(sale_order)
            result["WorkingDocuments"]["TotalCredit"] += utils.gross_total(sale.amount_untaxed)
            result["WorkingDocuments"]["NumberOfEntries"] += 1

        return result

    def _generate_sale_order(self, sale, status_code):
        return {
            "DocumentNumber": sale.name,
            "DocumentStatus": {
                "WorkStatus": status_code,
                "WorkStatusDate": self._format_date(sale.system_entry_date or sale.create_date),
                "SourceID": sale.user_id.id,
                "SourceBilling": "P",
            },
            "Hash": sale.hash or 0,
            "HashControl": sale.company_id.key_version or "0",
            "Period": fields.Date.to_string(sale.date_order)[5:7],
            "WorkDate": fields.Date.to_string(sale.date_order.date()),
            "WorkType": sale.type,
            "SourceID": sale.user_id.id,
            "SystemEntryDate": self._format_date(sale.system_entry_date or sale.create_date),
            "CustomerID": sale.partner_id.id if sale.partner_id.vat else "CF",
            "Line": [],
            "DocumentTotals": {
                "TaxPayable": utils.gross_total(sale.amount_tax),
                "NetTotal": utils.gross_total(sale.amount_untaxed),
                "GrossTotal": utils.gross_total(sale.amount_total),
                "Currency": {
                    "CurrencyCode": sale.currency_id.name,
                    "CurrencyAmount": utils.gross_total(sale.amount_total),
                    "ExchangeRate": sale.currency_id.rate,
                } if sale.currency_id != sale.company_id.currency_id else {},
            }
        }

    def _generate_line_data(self, line, sale):
        return {
            "LineNumber": line.id,
            "ProductCode": line.product_id.id or line.product_id.default_code,
            "ProductDescription": line.product_id.name[:200],
            "Quantity": line.product_uom_qty,
            "UnitOfMeasure": line.product_uom_id.name if sale.user_id.has_group('uom.group_uom') else "Unidade(s)",
            "UnitPrice": line.price_unit,
            "TaxPointDate": fields.Date.to_string(sale.date_order.date())[:10],
            "Description": line.product_id.name[:200],
            "CreditAmount": utils.gross_total(line.price_subtotal),
            "Tax": self._get_taxes_for_line(line)[0],
            "TaxExemptionReason": self._get_taxes_for_line(line)[1]["TaxExemptionReason"],
            "TaxExemptionCode": self._get_taxes_for_line(line)[1]["TaxExemptionCode"],
            "SettlementAmount": 0,  # montante do desconto da linha 4.3.4.14.18.
        }

    def _get_taxes_for_line(self, line):
        taxes = []
        exemption = {"TaxExemptionReason": "", "TaxExemptionCode": ""}
        for tax in line.tax_id.filtered(lambda r: r.tax_exigibility == "on_invoice"):
            tax_values = {
                "TaxType": tax.tax_type,
                "TaxCountryRegion": tax.country_region,
                "TaxCode": tax.tax_code if tax.tax_type != 'NS' else 'NS',
                "TaxPercentage": utils.gross_total(tax.amount) if tax.amount_type in ["percent",
                                                                                      "division"] else None,
                "TaxAmount": utils.gross_total(tax.amount) if tax.amount_type == "fixed" else None
            }
            taxes.append(tax_values)
            if tax.tax_exigibility == "on_invoice" and tax.amount == 0:
                exemption["TaxExemptionReason"] = tax.exemption_reason
                exemption["TaxExemptionCode"] = "M21"

        return taxes, exemption

    def _format_date(self, datetime):
        system_entry_date = datetime.isoformat(sep='T', timespec='seconds')
        return system_entry_date
