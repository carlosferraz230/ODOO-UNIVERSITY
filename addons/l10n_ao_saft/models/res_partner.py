from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import OrderedDict


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_saft_data(self):
        """
        Gera dados SAF-T para clientes e fornecedores, com tratamento para partner=None.
        """
        result = {
            "Customer": [],
            "Supplier": [],
        }

        def build_address(partner=None):
            """Constrói endereço SAF-T, mesmo se partner=None."""
            address = OrderedDict([
                ("StreetName", "Desconhecido"),
                ("AddressDetail", "Desconhecido"),
                ("City", "Desconhecido"),
                ("PostalCode", ""),
                ("Province", "Desconhecido"),
                ("Country", "AO"),
            ])
            if partner:
                address.update({
                    "StreetName": partner.street or "Desconhecido",
                    "AddressDetail": (partner.contact_address or "Desconhecido")[:249],
                    "City": partner.city or "Desconhecido",
                    "PostalCode": partner.zip or "",
                    "Province": partner.state_id.name if partner.state_id else "Desconhecido",
                    "Country": partner.country_id.code if partner.country_id else "AO",
                })
            return address

        # Cliente Genérico (Consumidor Final)
        result["Customer"].append(OrderedDict([
            ("CustomerID", "CF"),
            ("AccountID", "31121"),
            ("CustomerTaxID", "XXXXXXXXX"),
            ("CompanyName", "CONSUMIDOR FINAL"),
            ("BillingAddress", build_address()),
            ("ShipToAddress", build_address()),
            ("Telephone", "000000000"),
            ("Email", "Desconhecido"),
            ("Website", "Desconhecido"),
            ("SelfBillingIndicator", "0"),
        ]))

        # Processar parceiros reais
        for partner in self:
            # Validações para parceiros com VAT
            if partner.vat:
                if not partner.country_id:
                    raise ValidationError(_("País obrigatório para parceiro com NIF: %s") % partner.name)
                if not partner.city:
                    raise ValidationError(_("Cidade obrigatória para parceiro com NIF: %s") % partner.name)

                # Clientes
                if partner.customer_rank > 0:
                    customer_data = OrderedDict([
                        ("CustomerID", partner.ref or str(partner.id)),
                        ("AccountID", partner.property_account_receivable_id.code or "31121"),
                        ("CustomerTaxID", partner.vat or "500000000"),
                        ("CompanyName", partner.name),
                        ("BillingAddress", build_address(partner)),
                        ("ShipToAddress", build_address(partner)),
                        ("Telephone", str(partner.phone)[:19] if partner.phone else "000000000"),
                        ("Email", partner.email or "Desconhecido"),
                        ("Website", partner.website or "Desconhecido"),
                        ("SelfBillingIndicator", "0"),
                    ])
                    result["Customer"].append(customer_data)

                # Fornecedores
                if partner.supplier_rank > 0:
                    supplier_data = OrderedDict([
                        ("SupplierID", partner.ref or str(partner.id)),
                        ("AccountID", partner.property_account_payable_id.code or "2211"),
                        ("SupplierTaxID", partner.vat),
                        ("CompanyName", partner.name),
                        ("BillingAddress", build_address(partner)),
                        ("Telephone", str(partner.phone)[:19] if partner.phone else "000000000"),
                        ("Email", partner.email or "Desconhecido"),
                        ("Website", partner.website or "Desconhecido"),
                        ("SelfBillingIndicator", "1" if partner.self_billing else "0"),
                    ])
                    result["Supplier"].append(supplier_data)

        return result
