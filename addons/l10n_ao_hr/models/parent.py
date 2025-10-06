# -*- coding: utf-8 -*-
from odoo import models, fields


class HrFather(models.Model):
    _name = 'hr.father'
    _description = "Father"

    name = fields.Char('Name')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    state_id = fields.Char('State')
    zip = fields.Char('Zip')
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    child_ids = fields.Many2many('hr.employee', string='Childs(s)')


class HrMother(models.Model):
    _name = 'hr.mother'
    _description = "Mother"

    name = fields.Char('Name')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    city = fields.Char('City')
    state_id = fields.Char('State')
    zip = fields.Char('Zip')
    phone = fields.Char('Phone')
    mobile = fields.Char('Mobile')
    email = fields.Char('Email')
    child_ids = fields.Many2many('hr.employee', string='Childs(s)')
