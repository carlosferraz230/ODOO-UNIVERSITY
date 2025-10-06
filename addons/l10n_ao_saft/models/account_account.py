from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTAccountAccount(models.Model):
    _inherit = "account.account"

    @api.multi
    def get_content_saf_t_ao(self):

        start_date = self._context.get("date_from")
        end_date = self._context.get("date_to")
        customers = suppliers = self.env["res.partner"]
        taxes = self.env["account.tax"]
        journals = self.env["account.journal"]

        if not start_date or not end_date:
            raise ValidationError(_("Start date or end period date are not defined!"))

        result = {"GeneralLedgerAccounts": []}

        for account in self.filtered(lambda r: not r.deprecated):
            mov_debit_balance = mov_credit_balance = 0.0

            move_lines = self.env["account.move.line"].search(
                [("account_id", "=", account.id), ("date", ">=", start_date),
                 ("date", "<=", end_date)])

            if not move_lines:
                continue

            journals |= move_lines.mapped("journal_id")

            for line in move_lines:
                mov_debit_balance += line.debit
                mov_credit_balance += line.credit

                if line.journal_id.type == "sale":
                    customers |= line.partner_id
                elif line.journal_id.type == "purchase":
                    suppliers |= line.partner_id

                if line.tax_line_id:
                    taxes |= line.tax_line_id
                if line.tax_ids:
                    taxes |= line.tax_ids

            account_val = {
                "AccountID": account.code,
                "AccountDescription": account.name,
                "OpeningDebitBalance": account.opening_debit,
                "OpeningCreditBalance": account.opening_credit,
                "ClosingDebitBalance": mov_debit_balance,
                "ClosingCreditBalance": mov_credit_balance,
                "GroupingCategory": "GM",
                "GroupingCode": account.group_id.code_prefix_start,
            }
            result["GeneralLedgerAccounts"].append(account_val)
            result["Customers"] = customers
            result["Suppliers"] = suppliers
            result["Journals"] = journals
            result["Taxes"] = taxes

        return result