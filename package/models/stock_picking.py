# -*- coding: utf-8 -*-

from odoo import api,fields, models,_
from odoo.exceptions import ValidationError
from collections import defaultdict


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
        moves = self.package_order.sale_order_id.order_line.move_ids
        moves.filtered(lambda move: not move.picking_id.immediate_transfer
                           and move.state in ('confirmed', 'partially_available')
                           and (move._should_bypass_reservation()
                                or move.picking_type_id.reservation_method == 'at_confirm'
                                or (move.reservation_date and move.reservation_date <= fields.Date.today())))\
                 ._action_assign()
        return res