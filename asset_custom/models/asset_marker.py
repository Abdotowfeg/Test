# -*- coding: utf-8 -*-

from odoo import models, fields


class AssetMarker(models.Model):
    _name = 'asset.marker'
    _rec_name = 'name'
    _description = 'Asset Marker'

    name = fields.Char(string="Name", required=False, )
