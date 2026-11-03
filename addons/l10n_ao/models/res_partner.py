from contextlib import redirect_stderr

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _default_county(self):
        return self.env['res.country.state.county'].sudo().search([('code', '=', 'LDA')]).id

    @api.model
    def _default_country(self):
        return self.env.ref('base.ao')

    @api.onchange('state_id')
    def _onchange_state_id_id(self):
        if self.state_id:
            return {'domain': {'county_id': [('state_id', '=', self.state_id.id)]}}
        else:
            return {'domain': {'county_id': []}}

    customer = fields.Boolean(string="É Cliente?")
    supplier = fields.Boolean(string="É Fornecedor?")
    county_id = fields.Many2one(comodel_name="res.country.state.county", string="County", default=_default_county)
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', default=_default_country)

    @api.model_create_multi
    def create(self, values):
        # Company users create contacts for their own company by default.
        # System administrators may still create intentionally shared contacts.
        if not self.env.user.has_group('base.group_system'):
            for vals in values:
                if not vals.get('company_id'):
                    vals['company_id'] = self.env.company.id
        result = super(ResPartner, self).create(values)
        if self.env.user.company_id.automatic_partner_account:
            self._automatic_partner_account(result)
        return result

    def write(self, values):
        customer = values.get('customer')
        supplier = values.get('supplier')
        result = super(ResPartner, self).write(values)
        for res in self:
            if customer is not None:
                res.customer_rank = 1 if customer else 0
                res._automatic_partner_account(res)
            if supplier is not None:
                res.supplier_rank = 1 if supplier else 0
                res._automatic_partner_account(res)
        return result

    def _automatic_partner_account(self, partner):
        def create_account(name, code_prefix, account_type_str):
            seq = self.env['ir.sequence'].next_by_code(f'{account_type_str}.account')
            prefix = code_prefix
            code = f'{prefix}{seq}'

            account_type = self.env['account.account.type'].sudo().search([('type', '=', account_type_str)], limit=1)
            return self.env['account.account'].sudo().create({
                'name': name,
                'code': code,
                'user_type_id': account_type.id,
                'reconcile': True,
            })

        company_id = self.env.user.company_id.id
        country_ao = self.env['res.country'].sudo().search([('code', '=', 'AO')])
        is_local = partner.country_id == country_ao

        # Cliente
        if partner.customer_rank > 0 or self._context.get('search_default_customer'):
            expected_code = '311211'
            partner_account = self.env['account.account'].search([
                ('code', '=', expected_code),
                ('company_id', '=', company_id)
            ], limit=1)

            if partner.property_account_receivable_id.code == expected_code:
                prefix = self.env.user.company_id.partner_receivable_code_prefix if is_local else self.env.user.company_id.fpartner_receivable_code_prefix
                account = create_account(partner.name, prefix, 'receivable')

                if account:
                    partner.property_account_receivable_id = account.id
                else:
                    existing_account = self.env['account.account'].search([
                        ('company_id', '=', company_id),
                        ('name', '=', partner.name),
                        ('code', '=ilike', f'{prefix}%')
                    ], order='id desc', limit=1)
                    partner.property_account_receivable_id = existing_account.id

        # Fornecedor
        elif partner.supplier_rank > 0 or self._context.get('default_supplier'):
            expected_code = '32121'
            partner_account = self.env['account.account'].search([
                ('code', '=', expected_code),
                ('company_id', '=', company_id)
            ], limit=1)

            if partner.property_account_payable_id.code == expected_code:
                prefix = self.env.user.company_id.partner_payable_code_prefix if is_local else self.env.user.company_id.fpartner_payable_code_prefix
                account = create_account(partner.name, prefix, 'payable')

                if account:
                    partner.property_account_payable_id = account.id
                else:
                    existing_account = self.env['account.account'].search([
                        ('company_id', '=', company_id),
                        ('name', '=', partner.name),
                        ('code', '=ilike', f'{prefix}%')
                    ], order='id desc', limit=1)
                    partner.property_account_payable_id = existing_account.id

