{
    'name': 'Angola - Point of Sale',
    'category': 'Sales/Point of Sale',
    'summary': 'POS retail and restaurante',
    'description': "Solution for POS",

    'author': 'Ticblac Solution - Serviços, Lda',
    'depends': ['base', 'point_of_sale', 'l10n_ao'],
    'data': [

        #'data/res_partner.xml',

        'views/pos_session_view.xml',
        'views/pos_config_view.xml',
        # 'reports/session_close_report.xml',
    ],
    'assets': {

        'point_of_sale.assets': [
            'l10n_ao_pos/static/src/js/get_customer.js',
            'l10n_ao_pos/static/src/js/pos_invoice_number.js',
        ],
        'web.assets_qweb': [
            "l10n_ao_pos/static/src/xml/**/*",
        ],
    },
    'installable': True,
}
