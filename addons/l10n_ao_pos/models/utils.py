# -*- coding: utf-8 -*-
from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA1
from decimal import Decimal, ROUND_HALF_UP
import base64
from base64 import b64decode
from xml.dom.minidom import parseString

private_key = """-----BEGIN RSA PRIVATE KEY-----
MIICXwIBAAKBgQDFEfemR9u9d7q7RSO4tnU2rkoLULeTRBVsGTjhWw2D8ThRpqzQ
xls0l1fSFQtYz9hxijrn/gZoZYG1aaqbguh5fpLr9YLhgXydByCvvXFZXgTDM2n8
V4hMa5M+ivAbViSVjmHrDjEAbMlgDdBduaawCKFOlMFfp/8RAP+S9RiaPwIDAQAB
AoGBAJtXimtcgW5cjqlH2tyjlsm/oUZCHjLLnEdVqmyZpZG397kFNXxsn0BZfDRx
ujwLuoXlfIGaz9pDCXfDD2T+T9jymK+dyWYd4X9nFqPAJuz2y3AY4BJ6kwe4jew5
V3QMCbMWzvlqdgW9z+OgQUlJ/0hSE3Jz4zM/c/vYK+kc8xuhAkEA7pUZ42LQjSkN
I7xFpK1aFyy8V12ZXV2rQz3Ug91Q0QUtiLQuiYKDdjXDlL7Ysnq1HIqP2Cu75pa8
Fcwekwb3rQJBANN1CdZggfuGD9sJf0CxiZXkQy0UW7WTQg3X6vP3eDjRyb3fm3K+
3CstBpQzOqPSUG1eVtVfoRYSHCDSCxrJxxsCQQC8ZUK/Gt2CSmNUz6vS4Qyd9jZ3
arLbVkcR3vY8dnwFwef15gpFjakPpF7fy2BEd78iXYw+8DH9YRP+xmNySHM1AkEA
i1jxZqiqf8pU4I9doJBejryh2C82UG3+dYj4eFV4kFkPjWSx1+gWxw0g7MDlv9d0
0N3+cxZV3WmJx8cjMkAOSQJBAIW1J3N8wtlwU0Jb8fnUP+xaEsyJk7KOeudXsvFD
Wlbv5cYqT8okF4+32dfVkyFhe/AYpy0qllR2UhA//1ZLQXM=
-----END RSA PRIVATE KEY-----"""

public_key = ""

def gross_total(num):
    our_value = Decimal(num)
    output_value = Decimal(our_value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    return output_value

def signer(content_data):
    rsa_key = RSA.importKey(private_key)
    print(rsa_key)
    signed = PKCS1_v1_5.new(rsa_key)
    digest = SHA1.new()
    data = base64.b64encode(content_data.encode('ascii'))
    digest.update(b64decode(data))
    return base64.b64encode(signed.sign(digest))


def verify_signer(sin, content_data):
    rsa_key = RSA.importKey(public_key)
    signed = PKCS1_v1_5.new(rsa_key)
    digest = SHA1.new(content_data.encode("utf-8"))
    return signed.verify(digest, sin)

