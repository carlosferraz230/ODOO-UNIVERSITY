from odoo import models, fields, api, _
from . import utils

mechanisms = [('CD', 'Cartão débito'),
              ('CC', 'Cartão crédito'),
              ('MB', 'Referências de pagamento para Multicaixa'),
              ('NU', 'Numerário'),
              ('CI', 'Crédito documentário internacional'),
              ('CO', 'Cheque ou cartão oferta'),
              ('CS', 'Compensação de saldos em conta corrente'),
              ('DE', 'Dinheiro electrónico,por exemplo residente em cartões de fidelidade ou de pontos'),
              ('OU', 'Outros meios aqui não assilados'),
              ('PR', 'Permuta de bens'),
              ('TB', 'Transferência bancária')]


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_mechanism = fields.Selection(string="Payment Mechanism", selection=mechanisms)

    _sql_constraints = [('unique_reference', 'UNIQUE(payment_reference)',
                         '  de referência do pagamento deve ser único!')]

    payment_state = fields.Selection(related='move_id.payment_state')
    invoice_date = fields.Date(related='move_id.invoice_date')

    def get_saft_data(self):
        result = {
            'Payments': {
                "NumberOfEntries": 0,
                "TotalDebit": 0,
                "TotalCredit": 0,
                "Payment": [],
            }
        }

        payments = self.filtered(
            lambda payment: payment.state in ['paid', 'in_process', 'reconciled'] and
                            payment.company_id == self.env.company
        )

        for payment in payments:
            payment_status = 'A' if payment.state == 'cancelled' else 'N'
            payment_data = self._generate_payment_data(payment, payment_status)

            for inv in payment.invoice_ids:
                payment_data["Line"] = self._generate_invoice_line(inv, payment)
                if inv.move_type == "out_refund" and inv.state in ["posted"]:
                    result["Payments"]["TotalDebit"] += utils.gross_total(inv.amount_untaxed)
                elif inv.move_type == "out_invoice" and inv.state in ["posted"]:
                    result["Payments"]["TotalCredit"] += utils.gross_total(inv.amount_untaxed)

                payment_data["DocumentTotals"] = self._generate_document_totals(inv)

                withholding_tax = self._get_withholding_tax(inv)

                if withholding_tax:
                    payment_data["WithholdingTax"] = withholding_tax

            result['Payments']['Payment'].append(payment_data)
        result['Payments']['NumberOfEntries'] = len(payments)

        return result

    def _generate_payment_data(self, payment, payment_status):
        return {
            "PaymentRefNo": payment.receipt_no.replace('0', ''),
            "Period": fields.Date.to_string(payment.date)[5:7],
            "TransactionID": f"{fields.Date.to_string(payment.date)} {payment.journal_id.code.replace(' ', '')} {payment.name.replace('/', '').replace(' ', '')}",
            "TransactionDate": fields.Date.to_string(payment.date),
            "PaymentType": 'RG',
            "Description": payment.memo or "Pagamento + %s" % (payment.partner_id.name),
            "SystemID": payment.id,
            "DocumentStatus": {
                "PaymentStatus": payment_status,
                "PaymentStatusDate": payment.write_date.isoformat(sep='T', timespec='seconds'),
                "SourceID": payment.create_uid.id,
                "SourcePayment": 'P',
            },
            "PaymentMethod": {
                "PaymentMechanism": payment.payment_mechanism or 'TB',
                "PaymentAmount": utils.gross_total(payment.amount),
                "PaymentDate": fields.Date.to_string(payment.date),
            },
            "SourceID": payment.create_uid.id,
            "SystemEntryDate": payment.create_date.isoformat(sep='T', timespec='seconds'),
            "CustomerID": payment.partner_id.id if payment.partner_id.vat else "CF",
        }

    def _generate_invoice_line(self, inv, payment):
        taxes, exemption = self._generate_invoice_taxes(inv)
        line_data = {
            "LineNumber": inv.id,
            "SourceDocumentID": {
                "OriginatingON": inv.name,
                "InvoiceDate": fields.Date.to_string(inv.invoice_date),
                "Description": inv.name,
            },
            "SettlementAmount": utils.gross_total(0.0),  # sum(inv.invoice_line_ids.mapped("discount")),
            "DebitAmount": utils.gross_total(inv.amount_untaxed) if inv.move_type == "out_refund" else None,
            "CreditAmount": utils.gross_total(inv.amount_untaxed) if inv.move_type == "out_invoice" else None,
            "Tax": taxes,
            "TaxExemptionReason": exemption["TaxExemptionReason"],
            "TaxExemptionCode": exemption["TaxExemptionCode"]
        }
        return line_data

    def _generate_invoice_taxes(self, inv):
        taxes = []
        exemption = {"TaxExemptionReason": "", "TaxExemptionCode": ""}

        for line in inv.invoice_line_ids:
            for tax in line.tax_ids.filtered(lambda r: r.tax_exigibility == "on_invoice"):
                tax_values = {
                    "TaxType": tax.tax_type,
                    "TaxCountryRegion": tax.country_region,
                    "TaxCode": tax.tax_code if tax.tax_type != 'NS' else 'NS',
                    "TaxPercentage": utils.gross_total(tax.amount) if tax.amount_type in ["percent",
                                                                                          "division"] else None,
                    "TaxAmount": utils.gross_total(tax.amount) if tax.amount_type == "fixed" else None
                    # Use 0.0 instead of an empty dict
                }
                taxes.append(tax_values)

                if tax.tax_exigibility == "on_invoice" and tax.amount == 0:
                    exemption["TaxExemptionReason"] = tax.exemption_reason
                    exemption["TaxExemptionCode"] = "M21"

        return taxes, exemption  # Ensure return is outside of the loops

    def _generate_document_totals(self, inv):
        totals = {
            "TaxPayable": utils.gross_total(inv.amount_tax),
            "NetTotal": utils.gross_total(inv.amount_untaxed),
            "GrossTotal": utils.gross_total(inv.amount_total),
            "Settlement": {"SettlementAmount": 0.0},
        }

        if inv.currency_id != inv.company_id.currency_id:
            totals["Currency"] = {
                "CurrencyCode": inv.currency_id.name,
                "CurrencyAmount": utils.gross_total(inv.amount_total),
                "ExchangeRate": inv.currency_id.rate
            }

        return totals

    def _get_withholding_tax(self, inv):
        # Verificar se há algum imposto com exigibilidade "on_payment"
        tax_lines = [
            line for line in inv.invoice_line_ids
            if any(tax.tax_exigibility == "on_payment" for tax in line.tax_ids)
        ]

        # Se houver linhas com impostos "on_payment", geramos a lista
        if tax_lines:
            return [
                {
                    "WithholdingTaxType": tax.tax_type_with,
                    "WithholdingTaxDescription": tax.name,
                    "WithholdingTaxAmount": utils.gross_total(inv.amount_wth_apply),
                }
                for line in tax_lines
                for tax in line.tax_ids.filtered(lambda r: r.tax_exigibility == "on_payment")
            ]

        # Caso contrário, retornamos uma lista vazia
        return []

