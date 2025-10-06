from odoo import fields, models, api


class Schedule(models.Model):
    _inherit = 'resource.calendar'

    hours_per_week = fields.Float(string="Hours for week", compute="_compute_day_hours")
    days_per_week = fields.Float(string="Days for week", compute="_compute_week_days")

    @api.depends('attendance_ids')
    def _compute_week_days(self):
        for schedule in self:
            _qt_days = len(set([attendance.dayofweek for attendance in schedule.attendance_ids]))
            schedule.days_per_week = _qt_days

    @api.depends('hours_per_day')
    def _compute_day_hours(self):
        for schedule in self:
            schedule.hours_per_week = schedule.hours_per_day * schedule.days_per_week

