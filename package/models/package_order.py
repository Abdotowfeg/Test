# -*- coding: utf-8 -*-

from odoo import api,fields, models,_


class PackageOrder(models.Model):
    _name = 'package.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority desc'

    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'), ('2', 'Normal'), ('3', 'High')], string='Priority')

    package_service = fields.Many2one('product.product',string="Package Service",domain="[('detailed_type','=','service'),('package','=',True)]")
    user_id = fields.Many2one('res.users',string="Responsible",default=lambda self: self.env.user)
    company_id = fields.Many2one('res.company',string='Company',default=lambda self: self.env.company)
    date = fields.Datetime(string="Scheduled Date")
    material_ids = fields.One2many('package.material','order_id',string="Package Material")
    state = fields.Selection([('draft','Draft'),('confirm','Confirm'),('done','Done')],default='draft')
    sale_order_id = fields.Many2one('sale.order',string="Sale Order")
    picking_id = fields.Many2one('stock.picking',string="Package Delivery")


    @api.model
    def create(self,vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            if 'date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
            vals['name'] = self.env['ir.sequence'].next_by_code('package.order', sequence_date=seq_date) or _('New')

        result = super(PackageOrder, self).create(vals)
        return result

    def action_confirm(self):
        package_type = self.env['stock.picking.type'].search([('code','=','package_operation')],limit=1)
        move_list = []
        for line in self.material_ids:
            move_list.append((0,0,{
                'name':line.material_id.name,
                'product_id':line.material_id.id,
                'product_uom':line.unit_id.id,
                'product_uom_qty':line.material_qty,
                'location_id': package_type.default_location_src_id.id,
                'location_dest_id': package_type.default_location_dest_id.id,
            }))
        picking_out_pack = self.env['stock.picking'].create({
            'partner_id': self.sale_order_id.partner_id.id,
            'picking_type_id': package_type.id,
            'location_id': package_type.default_location_src_id.id,
            'location_dest_id': package_type.default_location_dest_id.id,
            'package_order':self.id,
            'move_lines':move_list
        })
        picking_out_pack.action_confirm()
        self.picking_id = picking_out_pack.id
        self.write({'state':'confirm'})  



    def action_view_picking(self):
        return {
            'name': 'Package Transfer',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id','=',self.picking_id.id)]

        }   


    def action_view_package_layers(self):
        self.ensure_one()
        scraps = self.env['stock.scrap'].search([('picking_id', '=', self.picking_id.id)])
        domain = [('id', 'in', (self.picking_id.move_lines + scraps.move_id).stock_valuation_layer_ids.ids)]
        action = self.env["ir.actions.actions"]._for_xml_id("stock_account.stock_valuation_layer_action")
        return dict(action, domain=domain)      



class PackageMaterial(models.Model):
    _name = 'package.material'

    order_id = fields.Many2one('package.order',string="Package Order")
    material_id = fields.Many2one('product.product',domain="[('detailed_type','=','product')]")    
    material_qty = fields.Float(string="Quantity")
    unit_id = fields.Many2one('uom.uom')
    price = fields.Float(string="Price",compute="_compute_price")


    @api.depends('material_qty')
    def _compute_price(self):
        for rec in self:
            rec.price = rec.material_id.list_price * rec.material_qty








