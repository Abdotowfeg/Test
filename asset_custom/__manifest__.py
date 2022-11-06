# -*- coding: utf-8 -*-
{
    'name': "Asset Custom",

    'summary': """
             Asset Custom Module.
        """,
    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'account_asset', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/account_asset_views.xml',
        'views/asset_marker_view.xml',
        'views/res_partner_view.xml',
        'views/hr_employee_view.xml'
    ],
}
