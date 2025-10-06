# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Projecto Expansão Odoo
# Copyright (C) 2025 Ticblac Solution - Serviços, Lda. All Rights Reserved
# http://www.ticblac.com.
{
    'name': 'Angola - Accounting',
    'version': '1.1',
    'author': 'Ticblac Solution - Serviços, Lda',
    'category': 'Localization',
    'summary': 'Angola - Accounting',
    'website': 'http://www.ticblac.com',
    'description': "Plano de contas PGC para Angola.",
    'depends': [
        'base',
        'account',
        'calendar',
        'account_accountant',
        'account_reports',
        'sale', 'sale_management',
        'purchase', 'purchase_stock',
        'stock', 'stock_account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/account_security.xml',

        "menu/menu.xml",

        'data/banks.xml',
        'data/country_state.xml',
        'data/country_state_county.xml',
        'data/account_sequence.xml',
        'data/l10n_ao_account_chart.xml',
        'data/account.account.template.csv',
        'data/account.group.template.csv',
        'data/account_chart_template.xml',
        'data/account_taxes.xml',
        'data/account_note_data.xml',
        'data/account_chart_template_configure_data.xml',

        'views/account_config_settings.xml',
        'views/account_account_view.xml',
        'views/account_tax_view.xml',
        'views/account_note_view.xml',
        'views/res_partner_view.xml',
        'views/banks_view.xml',
        'views/calendar_event_view.xml',
        'views/account_fiscal_year.xml',
        'views/account_move_view.xml',
        'views/account_payment_view.xml',
        'views/l10n_ao_sale_view.xml',
        'views/stock_picking_view.xml',

        'wizard/account_payment_register_view.xml',

        'reports/report.xml',
        'reports/invoice_report.xml',
        'reports/sale_report.xml'
    ],
}
