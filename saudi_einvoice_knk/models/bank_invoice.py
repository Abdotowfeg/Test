# -*- coding: utf-8 -*-
# Powered by Kanak Infosystems LLP.
# © 2020 Kanak Infosystems LLP. (<https://www.kanakinfosystems.com>).

import base64
from num2words import num2words
from odoo import api, fields, models, _


class BankInvoice(models.Model):
    _name = 'bank.invoice'

    name = fields.Char('Name')
    bank_number = fields.Char('Bank Number')
    bank_logo = fields.Binary('Bank Logo',store=True)
    move_id = fields.Many2one('account.move')   




    def name_get(self):
        result = []
        for record in self:
            if record.name:
                result.append((record.id, record.name + ''+'السداد على رقم حساب'))
        return result 
