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




class StockWarehousePackage(models.Model):
    _inherit = 'stock.warehouse'


    package_type_id = fields.Many2one(
        'stock.picking.type', 'Packaging Operation Type',
        domain=[('code', '=', 'package_operation')]) 



    def _get_picking_type_create_values(self, max_sequence):
        data, next_sequence = super(StockWarehousePackage, self)._get_picking_type_create_values(max_sequence)
        data.update({
            'package_type_id': {
                'name': _('Packaging'),
                'code': 'package_operation',
                'use_create_components_lots': True,
                'sequence': next_sequence + 2,
                'sequence_code': 'PACK',
                'company_id': self.company_id.id,
            }
        })
        return data, max_sequence + 4 



    def _get_sequence_values(self):
        values = super(StockWarehousePackage, self)._get_sequence_values()
        values.update({
            'package_type_id': {
                'name': self.name + ' ' + _('Sequence Package'),
                'prefix': self.code + '/PACK/',
                'padding': 5,
                'company_id': self.company_id.id
            }
        })
        return values  


    def _get_picking_type_update_values(self):
        data = super(StockWarehousePackage, self)._get_picking_type_update_values()
        package_dest_location = self.env['stock.location'].search([('usage','=','customer')])
        data.update({
            'package_type_id': {
                'default_location_src_id': self.lot_stock_id.id,
                'default_location_dest_id': package_dest_location.id,
                'barcode': self.code.replace(" ", "").upper() + "-Packaging",
            },
        })
        return data              