#-*- coding: utf-8 -*-
{
    'name': 'Sale Orderlines Import',
    'version': '16.0.1.0.1',
    'license': 'AGPL-3',
    'author': 'Thang Tong <nthang.tong@gmail.com>',
    'category': 'Sales',
    'website': 'https://github.com/thangtn86/sale_orderlines_import/tree/16.0',
    'summary': 'Adding button to import order lines on Quotation and Sale Orders',
    'depends': ['sale'],
    'data': [
        # 'Security',
        'security/ir.model.access.csv',

        # Wizards
        'wizards/import_sale_orderlines_views.xml',

        # Views
        'views/sale_order_views.xml',
    ],
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
