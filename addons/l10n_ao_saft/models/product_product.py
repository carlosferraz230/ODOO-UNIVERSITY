from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SAFTProductTemplateCompany(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("company_id") and not self.env.user.has_group("base.group_system"):
                vals["company_id"] = self.env.company.id
        return super().create(vals_list)


class SAFTProductTemplate(models.Model):
    _inherit = "product.product"

    unnumber = fields.Char(string="UNNumber", help="Preencher com o nª ONU para produtos perigosos")
    customs_details = fields.Char(string="Customs Details")

    def get_saft_data(self):
        """
        Gera os dados do SAFT AO relacionados aos produtos.
        Retorna um dicionário contendo informações estruturadas dos produtos.
        """
        result = {'Product': []}

        # Mapeamento do tipo de produto para o formato SAFT
        type_mapping = {
            "consu": "P",
            "service": "S",
            "product": "P",
        }

        for product in self:
            # Determina o tipo do produto usando o mapeamento
            product_type = type_mapping.get(product.type, "P")

            # Construção dos dados do produto
            product_data = {
                'ProductType': product_type,
                'ProductCode': product.id,
                'ProductGroup': (product.categ_id.name or "Desconhecido")[:49],
                'ProductDescription': (product.name or "Desconhecido")[:199],
                'ProductNumberCode': (product.default_code or "Desconhecido")[:59],
            }

            # Adiciona campos opcionais se disponíveis
            if product.unnumber:
                product_data['UNNumber'] = product.unnumber
            if product.customs_details:
                product_data['CustomsDetails'] = product.customs_details

            # Adiciona os dados do produto ao resultado
            result['Product'].append(product_data)

        return result
