# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.     
#
##############################################################################

# -------------------------------------------------------------
# Portuguese
# -------------------------------------------------------------
from odoo import _

to_19 = ('Zero', 'Um', 'Dois', 'Três', 'Quatro', 'Cinco', 'Seis',
         'Sete', 'Oito', 'Nove', 'Dez', 'Onze', 'Doze', 'Treze',
         'Catorze', 'Quinze', 'Dezasseis', 'Dezassete', 'Dezoito', 'Dezanove')

tens = ('Vinte', 'Trinta', 'Quarenta', 'Cinquenta', 'Sessenta', 'Setenta', 'Oitenta', 'Noventa')

to_900 = ('', 'Cento', 'Duzentos', 'Trezentos', 'Quatrocentos', 'Quinhentos', 'Seiscentos',
          'Setecentos', 'Oitocentos', 'Novecentos')

denom = ('',
         'Mil', 'Milhão', 'Mil Milhões', 'Bilião', 'Milhar de Bilião',
         'Trilião', 'Milhar de Trilião', 'Quatrilião', 'Milhar de Quatrilião', 'Quintilião',
         'Milhar de Quintilião', 'Sextilião', 'Milhar de Sextilião')

denom_plural = ('',
                'Mil', 'Milhões', 'Mil Milhões', 'Biliões', 'Milhar de Biliões',
                'Triliões', 'Milhar de Triliões', 'Quatriliões', 'Milhar de Quatriliões', 'Quintiliões',
                'Milhar de Quintiliões', 'Sextiliões', 'Milhar de Sextiliões')


# Função para determinar se o número é plural ou singular
def get_denomination(index, value):
    if value > 1:
        return denom_plural[index]
    return denom[index]


# Convert a value < 100 to Portuguese.
def _convert_nn(val):
    if val < 20:
        return to_19[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if val % 10:
                return dcap + '' + ' e ' + '' + to_19[val % 10]
            return dcap


# Convert a value < 1000 to Portuguese, special cased because it is the level that kicks
# off the < 100 special case. The rest are more general. This also allows you to
# get strings in the form of 'quarenta e cinco mil' if called directly.
def _convert_nnn(val):
    word = ''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        word = to_900[rem]
        if val == 100:
            word = 'Cem'
        if mod > 0:
            word = word + ' e '
    if mod > 0:
        word = word + _convert_nn(mod)
    return word


def portuguese_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
        return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            ret = _convert_nnn(l) + ' ' + get_denomination(didx, l)
            if mod == 1000 and l == 1:
                ret = 'Mil'
            if r > 0:
                ret = ret + ', ' + portuguese_number(r)
            return ret


def amount_to_text(number, currency_name):
    number = '%.2f' % number
    final_result = ""
    units_name = str(currency_name)
    list = str(number).split('.')
    start_word = portuguese_number(int(list[0]))  # Parte Inteira
    end_word = portuguese_number(int(list[1]))  # Parte Decimal
    cents_number = int(list[1])
    cents_name = (cents_number > 1 or cents_number == 0) and 'Cêntimos' or 'Cêntimo'
    if cents_number > 0:
        final_result = start_word + ' ' + units_name + ' e ' + end_word + ' ' + cents_name
    else:
        final_result = start_word + ' ' + units_name
    return final_result


# -------------------------------------------------------------
# Generic functions
# -------------------------------------------------------------

_translate_funcs = {'pt': amount_to_text}
