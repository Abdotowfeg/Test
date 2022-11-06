# -*- coding: utf-8 -*-

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _

INTERVAL_FACTOR = {
    'daily': 30.0,
    'weekly': 30.0 / 7.0,
    'monthly': 1.0,
    'yearly': 1.0 / 12.0,
}

PERIODS = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    sequence = fields.Char(string='Ref', required=False, copy=False, readonly=True,
                           states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    marker_id = fields.Many2one("asset.marker", string="Marker", required=False, readonly=True,
                                states={'draft': [('readonly', False)], 'model': [('readonly', False)]}, )
    partner_id = fields.Many2one("res.partner", string="Responsible", required=False,
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id),('is_employee', '!=', False)]")
    warranty_start_date = fields.Date(string="Warranty Start Date", required=False, default=fields.Date.context_today)
    warranty_end_date = fields.Date(string="Warranty End Date", required=False)
    warranty_period = fields.Integer(string="Warranty Period", required=False, )
    warranty_type = fields.Selection([('daily', 'Days'), ('weekly', 'Weeks'),
                                      ('monthly', 'Months'), ('yearly', 'Years'), ],
                                     string='Warranty Period Type', required=False,
                                     default='monthly', tracking=True, readonly=True,
                                     states={'draft': [('readonly', False)], 'model': [('readonly', False)]})
    image_128 = fields.Image()

    @api.model
    def create(self, vals):
        if vals.get('sequence', _('New')) == _('New'):
            vals['sequence'] = self.env['ir.sequence'].next_by_code('account.asset') or _('New')
        result = super(AccountAsset, self).create(vals)
        return result

    @api.onchange('model_id')
    def _onchange_model_id(self):
        model = self.model_id
        if model:
            self.method = model.method
            self.method_number = model.method_number
            self.method_period = model.method_period
            self.method_progress_factor = model.method_progress_factor
            self.prorata = model.prorata
            self.prorata_date = fields.Date.today()
            self.account_analytic_id = model.account_analytic_id.id
            self.analytic_tag_ids = [(6, 0, model.analytic_tag_ids.ids)]
            self.account_depreciation_id = model.account_depreciation_id
            self.account_depreciation_expense_id = model.account_depreciation_expense_id
            self.journal_id = model.journal_id
            self.account_asset_id = model.account_asset_id
            self.marker_id = model.marker_id

    @api.onchange('warranty_start_date', 'warranty_period', 'warranty_type')
    def onchange_date_start(self):
        if self.warranty_start_date:
            self.warranty_end_date = fields.Date.from_string(self.warranty_start_date) + relativedelta(**{
                PERIODS[
                    self.warranty_type]: self.warranty_period})
        else:
            self.warranty_end_date = False

    @api.onchange('account_analytic_id')
    def _onchange_account_analytic_id(self):
        asset_id = self.env['account.move'].search([('asset_id', '=', self._origin.id), ('state', '=', 'draft')])
        if asset_id:
            for rec in asset_id.line_ids:
                if rec.debit != 0.0:
                    rec.analytic_account_id = self.account_analytic_id.id
