# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2023 TICBLAC SOLUTION-SERVIÇOS, Lda. All Rights Reserved
# http://www.ticblac.com.
{
    'name': 'SAFT - Angola',
    'countries': ['ao'],
    'version': '1.1',
    'author': 'TICBLAC SOLUTION-SERVIÇOS, LDA',
    'category': 'Localization',
    'sequence': 1,
    'summary': 'SAFT - Angola',
    'website': 'http://www.ticblac.com',
    'description': "Regras fiscais com base AGT",
    'depends': [
        'sale',
        'account',
        'account_accountant',
        'stock',
        'l10n_ao',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/company_rules.xml',
        # 'data/parameter.xml',
        # 'data/saft_report.xml',
        # 'data/saft_report_purchase.xml',

        'views/saft_ao_view.xml',
        'views/res_company_view.xml',
        'views/account_tax_view.xml',
        'views/product_view.xml',
        'views/account_move_partner_company_view.xml',

        'wizards/saft_ao_wizard_view.xml',

        'reports/report_invoice_ao.xml',
        'reports/report_invoice_ticket.xml',
        'reports/report_sale_ao.xml',
    ],
    'installable': True,
    'auto_install': False,
}
