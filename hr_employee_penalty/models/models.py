# -*- coding: utf-8 -*-
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ViolationType(models.Model):
    """"""
    _name = 'violation.type'

    name = fields.Char(string="Name", translate=True)
    penalty_ids = fields.One2many("penalty", "violation_id", string="penalties")


class Penalty(models.Model):
    """"""
    _name = 'penalty'

    PENALTY_TYPES = [
        ("warning", "Warning"),
        ("deduction", "Deduction"),
        ("suspend", "Suspend"),
        ("stop_upgrade", "Stop Upgrade"),
        ("stop_bonus", "Stop Bonus"),
        ("termination", "Termination")
    ]

    DEDUCTION_TYPES = [
        ("percentage", "Percentage"),
        ("hour", "Hours"),
        ("day", "Days")
    ]

    name = fields.Char(string="Name", translate=True)
    violation_id = fields.Many2one("violation.type", string="Violation")
    sequence = fields.Integer(string="Sequence", default=1)
    penalty_period = fields.Integer(string="Penalty Period / Day", default=180)
    penalty_type = fields.Selection(PENALTY_TYPES, string="Penalty Type", default="warning")
    deduction_type = fields.Selection(DEDUCTION_TYPES, string="Deduction Type", default="day")
    deduction_percentage = fields.Float(string="Percentage Amount")
    deduction_period_hour = fields.Float(string="Deduction Period / Hours")
    deduction_period_day = fields.Float(string="Deduction Period / Days", default=5)
    suspend_period = fields.Integer(string="Suspend Period / Day", default=5)

    @api.constrains('sequence')
    def _check_sequence(self):
        for rec in self:
            if self.env['penalty'].search([('id', '!=', rec.id), ('sequence', '=', rec.sequence)]):
                raise ValidationError(_("Sequence must be unique per violation"))


class EmployeePenalty(models.Model):
    """"""
    _name = 'employee.penalty'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    STATE = [
        ('new', 'New'),
        ('waiting_approval', 'Waiting Approval'),
        ('approve', 'Applied'),
        ('cancel', 'Canceled'),
        ('refuse', 'Refused')
    ]

    state = fields.Selection(STATE, default='new', string='State', tracking=True)
    employee_id = fields.Many2one("hr.employee", string="Employee", tracking=True)
    department_id = fields.Many2one("hr.department", related="employee_id.department_id", string="Department")
    manager_id = fields.Many2one("hr.employee", related="employee_id.parent_id", string="Manager")
    employee_job = fields.Many2one("hr.job", related="employee_id.job_id", string="Job Position")
    employee_no = fields.Char(related="employee_id.pin", string="Employee No")
    violation_date = fields.Date(string="Violation Date", default=fields.Date.today(), tracking=True)
    applied_date = fields.Date(string="Applied Date")
    violation_id = fields.Many2one("violation.type", string="Violation Type", tracking=True)
    penalty_id = fields.Many2one("penalty", string="Penalty", copy=False)
    reason = fields.Text(string="Reason")
    employee_salary = fields.Float(string="Employee Salary")
    deduction_amount = fields.Float(string="Deduction Amount", compute="_get_deduction_amount")
    payslip_id = fields.Many2one("hr.payslip", string="Deducted in Payslip")

    @api.onchange('employee_id')
    def _get_employee_salary(self):
        for rec in self:
            rec.employee_salary = self.env["hr.contract"].search([('employee_id', '=', rec.employee_id.id),
                                                                  ('state', '=', 'open')], limit=1).wage

    @api.depends('employee_id', 'penalty_id')
    def _get_deduction_amount(self):
        for rec in self:
            employee_contract = self.env["hr.contract"].search([('employee_id', '=', rec.employee_id.id),
                                                                ('state', '=', 'open')], limit=1)
            rec.deduction_amount = 0.0
            if rec.penalty_id and rec.penalty_id.penalty_type in ('deduction', 'suspend'):
                if employee_contract:
                    hour_wage = (employee_contract.wage / (employee_contract.full_time_required_hours * 4))
                    day_wage = (hour_wage * employee_contract.resource_calendar_id.hours_per_day)

                    if rec.penalty_id.deduction_type == "percentage":
                        rec.deduction_amount = (day_wage * (rec.penalty_id.deduction_percentage / 100))
                    elif rec.penalty_id.deduction_type == "hour":
                        rec.deduction_amount = (rec.penalty_id.deduction_period_hour * hour_wage)
                    else:
                        rec.deduction_amount = (rec.penalty_id.deduction_period_day * day_wage)
                else:
                    raise ValidationError(_("Employee {} haven't running contract..."))

    @api.onchange('employee_id', 'violation_date', 'violation_id')
    def _get_penalty(self):
        # A function to get employee penalty depend on violation and last penalty
        for rec in self:
            penalties = self.env['penalty'].search([('violation_id', '=', rec.violation_id.id)], order="sequence DESC")
            last_penalty = self.env['employee.penalty'].search([('employee_id', '=', rec.employee_id.id),
                                                                ('violation_id', '=', rec.violation_id.id),
                                                                ('applied_date', '!=', False)
                                                                ],
                                                               order="id DESC", limit=1)
            if penalties:
                if last_penalty:
                    if (rec.violation_date - last_penalty.applied_date).days > last_penalty.penalty_id.penalty_period:
                        rec.penalty_id = penalties[-1].id
                    else:
                        for penalty in penalties:
                            if penalty.sequence > last_penalty.penalty_id.sequence:
                                rec.penalty_id = penalty.id
                    rec._all_penalties()
                else:
                    rec.penalty_id = penalties[-1].id

    def _all_penalties(self):
        if not self.penalty_id:
            raise ValidationError(_("All penalties for this violation are applied!"))

    def action_submit(self):

        body = ('<strong>You have new penalty<br/>click here to view it: </strong>')
        body += '<a href=# data-oe-model=employee.penalty data-oe-id=%d>%s</a>' % (self.id, self.employee_id.name)

        mail_details = {
            'subject': "{} Penalty".format(self.employee_id.name),
            'body': body,
            'partner_ids': [self.employee_id.address_home_id.id],
            'message_type': 'email',
            'email_to': self.employee_id.work_email
        }
        self.message_post(**mail_details)
        self.state = 'waiting_approval'
        self._check_bonus_upgrade()

    def action_approve(self):
        first_day = date(month=self.violation_date.month, year=self.violation_date.year, day=1)
        last_day = date(month=self.violation_date.month, year=self.violation_date.year, day=1
                        ) + relativedelta(months=1, days=-1)

        employee_contract = self.env["hr.contract"].search([('employee_id', '=', self.employee_id.id),
                                                            ('state', '=', 'open')], limit=1)
        hour_wage = (employee_contract.wage / (employee_contract.full_time_required_hours * 4))
        day_wage = (hour_wage * employee_contract.resource_calendar_id.hours_per_day)

        suspend_days = self.env['employee.penalty'].search([('penalty_id.penalty_type', '=', 'suspend'),
                                                            ('employee_id', '=', self.employee_id.id),
                                                            ('state', '=', 'approve'),
                                                            ('applied_date', '>=', first_day),
                                                            ('applied_date', '<=', last_day)])
        suspend_days = sum(days.penalty_id.suspend_period for days in suspend_days)

        deducted_month_days = self.env['employee.penalty'].search([('employee_id', '=', self.employee_id.id),
                                                                   ('state', '=', 'approve'),
                                                                   ('applied_date', '>=', first_day),
                                                                   ('applied_date', '<=', last_day)])

        deducted_month_days = sum(days.deduction_amount for days in deducted_month_days)

        if (suspend_days + self.penalty_id.suspend_period) > 5:
            raise ValidationError(_("A suspend of more than 5 days in month can't be applied!"))

        if (deducted_month_days + self.deduction_amount) > (day_wage * 5):
            raise ValidationError(_("A deduction of more than 5 days in month can't be applied!"))

        if self.deduction_amount > 0.0:
            if self.deduction_amount > (day_wage * 5):
                raise ValidationError(_("A deduction of more than 5 days salary can't be applied!"))

        if (fields.date.today() - self.violation_date).days > 30:
            raise ValidationError(_("This penalty has been exposed for more than 30 days, and it can't be applied!"))
        else:
            self.applied_date = fields.date.today()
            self.state = 'approve'
            self._check_bonus_upgrade()

    @api.returns('mail.message', lambda value: value.id)
    def message_post(self, **kwargs):
        return super(EmployeePenalty, self.with_context(
            mail_post_autofollow=self.env.context.get('mail_post_autofollow', True))).message_post(**kwargs)

    def action_cancel(self):
        self.state = 'cancel'
        self._check_bonus_upgrade()

    def action_refuse(self):
        self.state = 'refuse'
        self._check_bonus_upgrade()

    def action_new(self):
        self.applied_date = False
        self.state = 'new'
        self._check_bonus_upgrade()

    def _check_bonus_upgrade(self):
        employee_contract = self.env["hr.contract"].search([('employee_id', '=', self.employee_id.id),
                                                            ('state', '=', 'open')], limit=1)
        if self.state == 'approve':
            if self.penalty_id.penalty_type == 'stop_upgrade':
                employee_contract.stop_upgrade = True
            elif self.penalty_id.penalty_type == 'stop_bonus':
                employee_contract.stop_bonus = True
        else:
            employee_contract.stop_upgrade = False
            employee_contract.stop_bonus = False


class HRPayslip(models.Model):
    """"""
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        res = super(HRPayslip, self).compute_sheet()
        penalty_id = self.env.ref('hr_employee_penalty.employee_penalty_rule').id
        penalty_rule = self.env['hr.salary.rule'].search([('id', '=', penalty_id)])
        penalty_rule.amount_fix = 0.0

        employee_penalty = self.env['employee.penalty'].search([('employee_id', '=', self.employee_id.id),
                                                                ('state', '=', 'approve'),
                                                                ('applied_date', '>=', self.date_from),
                                                                ('applied_date', '<=', self.date_to),
                                                                ('payslip_id', '=', False)])

        for penalty in employee_penalty:
            penalty_rule.amount_fix = penalty_rule.amount_fix + penalty.deduction_amount
        return res

    def action_payslip_done(self):
        res = super(HRPayslip, self).action_payslip_done()
        employee_penalty = self.env['employee.penalty'].search([('employee_id', '=', self.employee_id.id),
                                                                ('penalty_id.penalty_type', 'in', ('deduction', 'suspend')),
                                                                ('state', '=', 'approve'),
                                                                ('applied_date', '>=', self.date_from),
                                                                ('applied_date', '<=', self.date_to),
                                                                ('payslip_id', '=', False)])
        for rec in employee_penalty:
            rec.payslip_id = self.id
        return res

    def action_payslip_cancel(self):
        res = super(HRPayslip, self).action_payslip_cancel()
        employee_penalty = self.env['employee.penalty'].search([('payslip_id', '=', self.id)])
        for rec in employee_penalty:
            rec.payslip_id = False
        return res


class HrContract(models.Model):
    """"""
    _inherit = 'hr.contract'

    stop_upgrade = fields.Boolean(string="Stop Upgrade", default=False)
    stop_bonus = fields.Boolean(string="Stop Bonus", default=False)


class HrEmployee(models.Model):
    """"""
    _inherit = 'hr.employee'

    penalty_count = fields.Integer(string="Penalties", compute="_get_penalty_count")

    def _get_penalty_count(self):
        self.penalty_count = self.env["employee.penalty"].search_count([('employee_id', '=', self.id)])

    def action_get_penalties(self):
        # This function is action to view employee penalties

        penalties = self.env["employee.penalty"].search([('employee_id', '=', self.id)])
        return {
            'name': '{} Penalties'.format(self.name),
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'employee.penalty',
            'domain': [('employee_id','in',penalties.mapped('employee_id.id'))]
        }
