from Crypto.PublicKey import RSA
from Crypto.Signature import PKCS1_v1_5
from Crypto.Hash import SHA1
from decimal import Decimal, ROUND_HALF_UP
import base64
from base64 import b64decode
import random
import string

private_key = ""

public_key = ""

agt_document_types = [
    ("FT", "Factura"),
    ("FT F", "Factura Fornecedor"), # Adicionado para facilitar odoo
    ("FT BI", "Factura Fornecedor"), # Adicionado para facilitar odoo
    ("FR", "Factura/recibo"),
    ("FR F", "Factura/recibo Fornecedor"), # Adicionado para facilitar odoo
    ("VD", "Venda a dinheiro"),
    ("GF", "Factura genérica"),
    ("FG", "Factura global"),
    ("ND", "Nota de débito"),
    ("NC", "Nota de crédito"),
    ("GR", "Guia de remessa"),
    ("AF", "Factura/recibo (autofaturação)"),
    ("TV", "Talão de venda"),
    ("TS", "Talão de serviços prestados"),
    ("TD", "Talão de devolução"),
    ("AA", "Alienação de activos"),
    ("DA", "Devolução de activos"),
]

move_type = ''
def check_agt_document_type(journal_code):
    for code, description in agt_document_types:
        if code == journal_code:
            return True
    return False

def agt_to_sign(content_data):
    rsa_key = RSA.importKey(private_key)
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

def gross_total(value):
    our_value = Decimal(value)
    output_value = Decimal(our_value.quantize(Decimal('.01'), rounding=ROUND_HALF_UP))
    return output_value


def generate_hash(tamanho=10):
    caracteres = string.ascii_uppercase + string.digits  # A-Z e 0-9
    return ''.join(random.choice(caracteres) for _ in range(tamanho))