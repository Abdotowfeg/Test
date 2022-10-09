# -*- coding: utf-8 -*-
##############################################################################
#
{
    'name': "Package",
    'version': "0.1",
    'author': " ",
    'website': " ",
    'category': "Hidden",
    'description': """ 
""",
    'depends': ['product','sale'],
    'data': [
        'security/ir.model.access.csv',
        'data/package_sequence_data.xml',
        'views/package_menu_view.xml',
        'views/package_order_view.xml',
        'views/product_views.xml',
        'views/sale_order_views.xml',

    ],
    'installable': True,
    'auto_install': False,
    
}
