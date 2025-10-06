from odoo import fields, models, api, _


class AOAccountConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    account_fiscal_year = fields.Many2one(related='company_id.accounting_year', required=1, readonly=False)
    automatic_partner_account = fields.Boolean(related="company_id.automatic_partner_account", readonly=False)
    inv_signed = fields.Boolean(related='company_id.inv_signed', readonly=False)
    partner_receivable_code_prefix = fields.Char(related="company_id.partner_receivable_code_prefix", readonly=False)
    partner_payable_code_prefix = fields.Char(related="company_id.partner_payable_code_prefix", readonly=False)
    fpartner_receivable_code_prefix = fields.Char(related="company_id.fpartner_receivable_code_prefix", readonly=False)
    fpartner_payable_code_prefix = fields.Char(related="company_id.fpartner_payable_code_prefix", readonly=False)
    # employee_payslip_code_prefix = fields.Char(related="company_id.employee_payslip_code_prefix")
    # employee_advance_code_prefix = fields.Char(related="company_id.employee_advance_code_prefix")
    # company_inss_account_code = fields.Char(related="company_id.company_inss_account_code")
    # tax_withhold_journal_id = fields.Many2one(related='company_id.tax_withhold_journal_id')
    # tax_withhold_received_account_id = fields.Many2one(related="company_id.tax_withhold_received_account_id")
    # tax_withhold_sent_account_id = fields.Many2one(related="company_id.tax_withhold_sent_account_id")
    # transfer_message = fields.Text("Message", related="company_id.transfer_message")
    # sale_cost_center = fields.Boolean(related='company_id.sale_cost_center')
    # invoice_cost_center = fields.Boolean(related='company_id.invoice_cost_center')
    # purchase_cost_center = fields.Boolean(related='company_id.purchase_cost_center')
    # stock_cost_center = fields.Boolean(related='company_id.stock_cost_center')
