# -*- coding: utf-8 -*-
from decimal import Decimal, ROUND_HALF_UP


def gross_total(num):
    our_value = Decimal(num)
    output_value = Decimal(our_value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    return output_value

def extract_period(date):
    period = str(date).split('-')

    if period:
        return period[1]
    return 12
