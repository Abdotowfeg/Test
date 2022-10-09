# -*- coding: utf-8 -*-

from odoo import fields, models,_
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    package_order = fields.Many2one('package.order',string="Package Order")

    def button_validate(self):
        if self.sale_id and self.sale_id.package_count > 0:
            for package in self.sale_id.package_order_id:
                if package.state != 'done':
                    raise ValidationError(_('You can not validate deilvery if package order is not done'))
        res = super(StockPicking, self).button_validate()
        self.package_order.state = 'done'
        return res


    


