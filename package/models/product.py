# -*- coding: utf-8 -*-

from odoo import fields, models


class Product(models.Model):
    _inherit = 'product.template'

    package = fields.Boolean(string="Package")
    material_ids = fields.One2many('bill.material','product_id',string="Product Bill Of Material")




class BillOfMaterial(models.Model):
    _name = 'bill.material'

    product_id = fields.Many2one('product.template',string="Product")
    material_id = fields.Many2one('product.product',domain="[('detailed_type','=','product')]")    
    uom_id = fields.Many2one('uom.uom',related="material_id.uom_id")
