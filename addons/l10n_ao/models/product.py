from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _rec_name = 'name'

    @api.onchange('detailed_type', 'categ_id')
    def _onchange_product_type(self):
        code_sale = '61'
        code_purchase = '21'
        if self.detailed_type == 'service':
            self.sale_ok = True
            code_sale = '6211'
            code_purchase = '752391' or '75219'
            account = self.env['account.account'].search([('code', '=', code_sale)])
            account_purchase = self.env['account.account'].search([('code', '=', code_purchase)])
            self.property_account_income_id = account
            self.property_account_expense_id = account_purchase
        elif self.detailed_type == 'product':
            self.sale_ok = True
            code_sale += '31'
            code_purchase += '21'
            account = self.env['account.account'].search([('code', '=', code_sale)])
            account_purchase = self.env['account.account'].search([('code', '=', code_purchase)])
            self.property_account_income_id = account
            self.property_account_expense_id = account_purchase
        elif self.detailed_type == 'consu':
            self.sale_ok = False
            code_sale = '752391' or '75219'
            account = self.env['account.account'].search([('code', '=', code_sale)])
            self.property_account_income_id = False
            self.property_account_expense_id = account

    @api.constrains('name', 'list_price', 'standard_price')
    def check_sale_price(self):
        for res in self:
            if res.list_price < 0:
                res.list_price = 0
            if res.standard_price < 0:
                res.standard_price = 0
