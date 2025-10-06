from odoo import models, fields


class AccountTaxTemplate(models.Model):
    _inherit = 'account.tax.template'

    tax_exigibility = fields.Selection(selection_add=[('withholding', 'Withholding')])
    threshold_wht = fields.Float("Threshold Amount", default=0,
                                 help="Withholding Tax will be applied only if base amount >= to threshold amount")
    code = fields.Char(string="Code")
    exemption_reason = fields.Char(string="Exemption Reason")
    tax_type = fields.Char(string="Tax Type")
    tax_code = fields.Char(string="Tax Code")


class AccountTax(models.Model):
    _inherit = 'account.tax'

    tax_exigibility = fields.Selection(selection_add=[('withholding', 'Withholding')])
    threshold_wht = fields.Float("Threshold Amount", default=0,
                                 help="Withholding Tax will be applied only if base amount >= to threshold amount")
    code = fields.Char(string="Code")
    exemption_reason = fields.Char(string="Exemption Reason")
    tax_type = fields.Char(string="Tax Type")
    tax_code = fields.Char(string="Tax Code")

    def _compute_amount(self, base_amount, price_unit, quantity=1.0, product=None, partner=None):
        """ Returns the amount of a single tax. base_amount is the actual amount on which the tax is applied, which is
            price_unit * quantity eventually affected by previous taxes (if tax is include_base_amount XOR price_include)
        """
        self.ensure_one()

        if self.amount_type == 'fixed':
            # Use copysign to take into account the sign of the base amount which includes the sign
            # of the quantity and the sign of the price_unit
            # Amount is the fixed price for the tax, it can be negative
            # Base amount included the sign of the quantity and the sign of the unit price and when
            # a product is returned, it can be done either by changing the sign of quantity or by changing the
            # sign of the price unit.
            # When the price unit is equal to 0, the sign of the quantity is absorbed in base_amount then
            # a "else" case is needed.
            if base_amount:
                return math.copysign(quantity, base_amount) * self.amount
            else:
                return quantity * self.amount

        price_include = self._context.get('force_price_include', self.price_include)

        if self.tax_exigibility == 'withholding' and self.threshold_wht > 0 and base_amount < self.threshold_wht:
            return 0
        # base * (1 + tax_amount) = new_base
        if self.amount_type == 'percent' and not price_include:
            return base_amount * self.amount / 100
        # <=> new_base = base / (1 + tax_amount)
        if self.amount_type == 'percent' and price_include:
            return base_amount - (base_amount / (1 + self.amount / 100))
        # base / (1 - tax_amount) = new_base
        if self.amount_type == 'division' and not price_include:
            return base_amount / (1 - self.amount / 100) - base_amount if (1 - self.amount / 100) else 0.0
        # <=> new_base * (1 - tax_amount) = base
        if self.amount_type == 'division' and price_include:
            return base_amount - (base_amount * (self.amount / 100))


