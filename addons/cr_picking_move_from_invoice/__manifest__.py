# -*- coding: utf-8 -*-
# Part of Creyox Technologies
{
    'name': 'Stock Picking/Move From invoice',
    "author": "Creyox Technologies",
    "website": "https://www.creyox.com",
    "support": "support@creyox.com",
    'category': 'Warehouse',
    'version': '15.0',
    'license': 'LGPL-3',
    'summary': 'It Creates the Stock Picking or Move From invoice or Vendor Bills',
    'description': """
     This module contains all the common features of creating the stock picking or stock moves from the invoice or vendor bill.""",
    'depends': ['base', 'account', 'sale_stock', 'sale', 'stock'],
    'data': [
        'views/config_parameter_view.xml',
        'views/account_move_inherit_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    "images": ["static/description/banner.png"],
    "price": 0,
    "currency": "USD"
}
