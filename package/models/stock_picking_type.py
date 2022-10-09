# -*- coding: utf-8 -*-

from odoo import fields, models,_
from datetime import datetime


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[
        ('package_operation', 'Packaging')
    ], ondelete={'package_operation': 'cascade'})


    


