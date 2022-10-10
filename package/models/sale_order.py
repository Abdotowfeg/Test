# -*- coding: utf-8 -*-

from odoo import api,fields, models,_
from datetime import datetime


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    package_order_id = fields.One2many('package.order','sale_order_id',string="Package Orders")
    package_count = fields.Integer(string="Package Count",compute="_compute_package_count")
    is_packaging = fields.Boolean(string="Is Packaging",compute="_compute_is_package")


    @api.onchange('order_line.product_id')
    def _compute_is_package(self):
        self.is_packaging = False
        for line in self.order_line:
            if line.product_id.package == True:
                self.is_packaging = True

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for line in self.order_line:
            list_val = []
            if line.product_id.detailed_type == 'service' and line.product_id.package == True:
                for line1 in line.product_id.material_ids:
                    list_val.append((0,0,{
                        'material_id':line1.material_id.id,
                        'material_qty':line1.material_qty,
                        'unit_id':line1.uom_id.id,
                        'price':line1.material_price,
                    }))
                package = self.env['package.order'].create({
                    'package_service':line.product_id.id,
                    'date':fields.Datetime.now(),
                    'state':'draft',
                    'material_ids':list_val
                    })
                package.write({'sale_order_id':self.id})
        return res  



    def action_view_package_order(self):
        return {
            'name': 'Package Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'package.order',
            'view_mode': 'tree,form',
            'target': 'current',
            'context': {
                'default_sale_order_id': self.id,
            },
            'domain':[('sale_order_id','=',self.id)]

        }    


    def _compute_package_count(self):
        self.package_count = len(self.package_order_id)          

    


