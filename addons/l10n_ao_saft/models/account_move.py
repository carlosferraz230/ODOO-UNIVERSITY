# -*- coding: utf-8 -*-
from typing import Dict, Any

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from . import utils
from odoo.tools import float_is_zero, float_compare, date_utils, DEFAULT_SERVER_DATE_FORMAT
from collections import defaultdict
from odoo.tools.misc import formatLang
from odoo.addons.l10n_ao.models import amount_to_text_pt


class SAFTAccountMove(models.Model):
    _inherit = 'account.move'

    def _check_customer_invoice_required_fields(self):
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund', 'out_receipt'):
                continue
            if not move.partner_id:
                raise ValidationError(_('Por favor, adicione um Cliente.'))
            if not move.invoice_date:
                raise ValidationError(_('Por favor, adicione uma Data à factura.'))
            lines = move.invoice_line_ids.filtered(lambda line: not line.display_type)
            if not lines:
                raise ValidationError(_('Por favor, adicione um produto.'))
            if any(not line.product_id for line in lines):
                raise ValidationError(_('Por favor, adicione um produto em cada linha da factura.'))
            if any(not line.tax_ids for line in lines):
                raise ValidationError(_('Por favor, adicione IVA em cada linha da factura.'))

    def action_post(self):
        for move in self:
            if move.move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                move._check_customer_invoice_required_fields()
        return super().action_post()

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if (
            'partner_id' in fields_list
            and not self.env.context.get('default_partner_id')
            and (values.get('move_type') or self.env.context.get('default_move_type')) in ('out_invoice', 'out_refund', 'out_receipt')
        ):
            values['partner_id'] = self.env['res.partner'].get_final_consumer(
                values.get('company_id') or self.env.company.id
            ).id
        return values

    @api.model
    def create(self, vals):
        move_type = vals.get('move_type') or self.env.context.get('default_move_type')
        if move_type in ('out_invoice', 'out_refund', 'out_receipt') and not vals.get('partner_id') and not self.env.context.get('default_partner_id'):
            vals['partner_id'] = self.env['res.partner'].get_final_consumer(
                vals.get('company_id') or self.env.company.id
            ).id
        return super().create(vals)

    def ticket_print_datetime(self):
        self.ensure_one()
        return fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime('%Y-%m-%d %H:%M:%S')

    def ticket_amount_in_words(self):
        self.ensure_one()
        currency_names = {
            'AOA': 'Kwanzas',
            'EUR': 'Euros',
            'USD': 'Dólares Americanos',
        }
        return amount_to_text_pt.amount_to_text(
            self.amount_total, currency_names.get(self.currency_id.name, self.currency_id.name)
        )

    settlement_discount = fields.Char(string="Settlement Discount")
    settlement_amount = fields.Float(string="Settlement Amount")
    settlement_date = fields.Date(string="Settlement Date")
    content_sign = fields.Char(string="Content to Sign")
    transaction_type = fields.Selection(string="Tipo de Lançamento",
                                        required=True,
                                        selection=[('N', 'Normal'),
                                                   ('R', 'Regularizações'),
                                                   ('A', 'Apur. Resultados'),
                                                   ('J', 'Ajustamentos')],
                                        help="Categorias para classificar os movimentos contabilísticos ao exportar o SAFT",
                                        default="N")

    def get_supplier_saft_data(self):
        """
        Generate SAFT-AO for supplier invoice data.
        """

        def format_document_totals(invoice):
            """
            Format the 'DocumentTotals' section of the invoice.
            """
            return {
                "TaxPayable": format(invoice.amount_tax, '.2f') if invoice.amount_tax else "0.00",
                "NetTotal": format(invoice.amount_untaxed, '.2f'),
                "GrossTotal": format(invoice.amount_total, '.2f'),
                **(
                    {
                        "Currency": {
                            "CurrencyCode": invoice.currency_id.name,
                            "CurrencyAmount": invoice.amount_total,
                            "ExchangeRate": invoice.currency_id.rate or 0,
                        }
                    } if invoice.currency_id.name != 'AOA' else {}
                ),

            }

        def format_withholding_tax(invoice):
            """
            Format the 'WithholdingTax' section of the invoice.
            """
            return [
                {
                    "WithholdingTaxType": tax.tax_type,
                    "WithholdingTaxDescription": tax.name,
                    "WithholdingTaxAmount": utils.gross_total(tax.amount),
                }
                for tax in invoice.tax_ids.filtered(lambda r: r.tax_type == "IVA")
            ]

        # Base structure for the result
        result = {
            "PurchaseInvoices": {
                "NumberOfEntries": 0,
                "Invoice": []
            }
        }

        # Filter supplier invoices
        invoices = self.filtered(
            lambda inv: inv.state == 'posted' and inv.move_type == "in_invoice" and inv.company_id == self.env.company
        )

        # Generate supplier invoice data
        for invoice in invoices:
            supplier_data = {
                "InvoiceNo": invoice.name,
                "Hash": invoice.hash or "",
                "SourceID": invoice.user_id.id,
                "Period": int(fields.Date.to_string(invoice.invoice_date)[5:7]),
                "InvoiceDate": fields.Date.to_string(invoice.invoice_date),
                "PurchaseType": "FT",
                "SupplierID": invoice.partner_id.id or invoice.partner_id.ref,
                "DocumentTotals": format_document_totals(invoice),
                **({"WithholdingTax": format_withholding_tax(invoice)} if format_withholding_tax(invoice) else {}),
            }

            result["PurchaseInvoices"]["Invoice"].append(supplier_data)

        # Update the number of entries
        result["PurchaseInvoices"]["NumberOfEntries"] = len(invoices)

        return result

    def get_saft_data(self):
        """
        Returns a list of invoices in SAFT AO format.
        :return: dict with sales invoices data
        """

        def valiinvoice_dates(invoices):
            """
            Validate invoices for missing tax, empty exemption reasons, or missing products.
            """
            bug_values = {
                'invoice_no_Tax': [],
                'empty_exemption_reason': [],
            }

            for inv in invoices:
                # Validate invoice lines for tax issues
                if not any(
                        line.tax_ids.filtered(
                            lambda tax: tax.tax_code in ['NOR', 'ISE', 'RED', 'OUT',
                                                         'INT'] and tax.tax_type == 'IVA'
                                        or tax.tax_code == 'NS' and tax.tax_type == 'NS'
                        )
                        for line in inv.invoice_line_ids
                ):
                    bug_values['invoice_no_Tax'].append(str(inv.name))

                # Validate individual lines
                for line in inv.invoice_line_ids.filtered(lambda l: not l.display_type):
                    if line.tax_ids.filtered(lambda t: t.tax_code == 'ISE' and not t.exemption_reason):
                        bug_values['empty_exemption_reason'].append(inv.name)

            return {key: list(set(value)) for key, value in bug_values.items()}

        def raise_errors(bug_values):
            """
            Raise validation errors based on identified bugs in invoices.
            """
            error_msgs = []
            if bug_values['invoice_no_Tax']:
                error_msgs.append(
                    _("As seguintes faturas não têm impostos configurados: %s\n"
                      "Rever em [Configurações > Contabilidade > Impostos]") % ", ".join(bug_values['invoice_no_Tax'])
                )
            if bug_values['empty_exemption_reason']:
                error_msgs.append(
                    _("Faturas com isenção de IVA mas faltando motivos: %s\n"
                      "Por exemplo: Isento nos termos da alínea l) do nº1 do artigo 12º do CIVA\n"
                      "Rever em [Configurações > Contabilidade > Impostos]") % ", ".join(bug_values['empty_exemption_reason'])
                )
            if error_msgs:
                raise ValidationError("\n".join(error_msgs))

        def get_taxes_for_line(line):
            taxes = []
            exemption = {"TaxExemptionReason": "", "TaxExemptionCode": ""}
            for tax in line.tax_ids.filtered(lambda r: r.tax_exigibility == "on_invoice"):
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

        def generate_line_data(invoice):
            return [
                {
                    "LineNumber": line.id,
                    "OrderReferences": {
                        "OriginatingON": invoice.ref,
                        "OrderDate": fields.Date.to_string(invoice.date)
                    } if invoice.move_type == "out_refund" else {},
                    "ProductCode": line.product_id.id,
                    "ProductDescription": line.name[:199] or line.product_id.name[:199],
                    "Quantity": line.quantity,
                    "UnitOfMeasure": line.product_uom_id.name if invoice.user_id.has_group('uom.group_uom') else "Unidade(s)",
                    "UnitPrice": format(line.price_unit * (1 - (line.discount or 0.0) / 100.0), '.2f'),
                    "TaxPointDate": fields.Date.to_string(invoice.invoice_date_due),
                    "References": {
                        "Reference": invoice.ref,
                        "Reason": invoice.ref or "",
                    } if invoice.move_type == "out_refund" else {},
                    "Description": line.product_id.name,
                    "ProductSerialNumber": {"SerialNumber": line.product_id.barcode or "S/N"},
                    "DebitAmount": utils.gross_total(line.price_subtotal) if invoice.move_type == "out_refund" else {},
                    "CreditAmount": utils.gross_total(
                        line.price_subtotal) if invoice.move_type == "out_invoice" else {},
                    "Tax": get_taxes_for_line(line)[0],
                    "TaxExemptionReason": get_taxes_for_line(line)[1]["TaxExemptionReason"],
                    "TaxExemptionCode": get_taxes_for_line(line)[1]["TaxExemptionCode"]

                }
                for line in invoice.invoice_line_ids if not line.display_type or line.display_type == 'product'
            ]

        def prepare_invoice_data(invoice):
            """
            Prepare data for a single invoice in SAFT format.
            """
            system_entry_date = (
                    invoice.system_entry_date or fields.Datetime.now()
            ).isoformat(sep='T', timespec='seconds')

            status_code = 'N'
            if invoice.journal_id.self_billing:
                status_code = 'S'
            elif invoice.state == 'posted' and invoice.payment_state == 'reversed':
                status_code = 'A'

            return {
                "InvoiceNo": invoice.name,
                "DocumentStatus": {
                    "InvoiceStatus": status_code,
                    "InvoiceStatusDate": system_entry_date,
                    "Reason": invoice.name[:48],
                    "SourceID": invoice.user_id.id,
                    "SourceBilling": "P",
                },
                "Hash": invoice.hash or "",
                "HashControl": invoice.company_id.key_version or "0",
                "Period": fields.Date.to_string(invoice.invoice_date)[5:7],
                "InvoiceDate": fields.Date.to_string(invoice.invoice_date),
                "InvoiceType": "NC" if invoice.move_type == "out_refund" else "FT",
                "SpecialRegimes": {
                    "SelfBillingIndicator": "1" if invoice.journal_id.self_billing else "0",
                    "CashVATSchemeIndicator": "1" if invoice.company_id.agt_regime == 'RC' else "0",
                    "ThirdPartiesBillingIndicator": "0",
                },
                "SourceID": invoice.user_id.id,
                # "EACCode": "N/A",
                "SystemEntryDate": system_entry_date,
                "TransactionID": "%s %s %s" % (
                    fields.Date.to_string(invoice.date), invoice.journal_id.code.replace(' ', ''),
                    invoice.name.replace(' ', '').replace('/', '')) if invoice.name else "",
                "CustomerID": invoice.partner_id.id if invoice.partner_id.vat else "CF",
                # "ShipTo": "",  # TODO: 4.1.4.15
                # "ShipFrom": "",  # TODO: 4.1.4.16
                # "MovementEndTime": "",  # TODO: 4.1.4.17,
                "MovementStartTime": system_entry_date,
                "Line": generate_line_data(invoice),
                "DocumentTotals": {
                    "TaxPayable": format(invoice.amount_tax, '.2f'),
                    "NetTotal": format(invoice.amount_untaxed, '.2f'),
                    "GrossTotal": format(invoice.amount_total, '.2f'),
                    "Currency": {
                        "CurrencyCode": invoice.currency_id.name,
                        "CurrencyAmount": utils.gross_total(invoice.amount_total),
                        "ExchangeRate": invoice.currency_id.rate,
                    } if invoice.currency_id != invoice.company_id.currency_id else {},
                    "Settlement": {
                        "SettlementDiscount": invoice.settlement_discount or 0,
                        "SettlementAmount": invoice.settlement_amount or 0,
                        "PaymentTerms": invoice.invoice_payment_term_id.name if invoice.invoice_payment_term_id.name else "",
                    },
                    "Payments": [
                        {
                            "PaymentMechanism": payment.payment_mechanism or "TB",
                            "PaymentAmount": utils.gross_total(payment.amount),
                            "PaymentDate": payment.date,
                        }
                        for payment in invoice.authorized_transaction_ids
                    ] if invoice.authorized_transaction_ids else [],
                },
                "WithholdingTax": [
                    {
                        "WithholdingTaxType": tax.tax_type_with,
                        "WithholdingTaxDescription": tax.name,
                        "WithholdingTaxAmount": utils.gross_total(invoice.amount_wth_apply),
                    }
                    for tax in invoice.tax_of_invoice() if tax.tax_exigibility == "withholding"
                ]
            },

        # Main processing
        invoices = self.filtered(
            lambda inv: inv.state == 'posted' and
                        inv.move_type in ['out_invoice', 'out_refund'] and
                        inv.company_id == self.env.company
        )
        bug_values = valiinvoice_dates(invoices)
        raise_errors(bug_values)

        sales_invoices = [prepare_invoice_data(inv) for inv in invoices]
        return {
            "SalesInvoices": {
                "NumberOfEntries": len(sales_invoices),
                "TotalDebit": sum(inv.amount_untaxed for inv in invoices if inv.move_type == 'out_refund'),
                "TotalCredit": sum(inv.amount_untaxed for inv in invoices if inv.move_type == 'out_invoice'),
                "Invoice": sales_invoices,
            }
        }

