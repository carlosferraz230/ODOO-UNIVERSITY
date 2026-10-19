import xml.etree.ElementTree as ET
from datetime import datetime
from odoo import models, fields, api
from . import valid_xml
from odoo.exceptions import AccessError, ValidationError
import  os

def dict_clean_up(value, var):
    new_dict = {}
    if hasattr(var, 'items'):
        for k, v in var.copy().items():
            if v == value:
                var.pop(k, None)
            elif isinstance(v, dict):
                new_v = dict_clean_up(value, v)
                new_dict[k] = new_v
            elif isinstance(v, list):
                val_list = []
                for d in v:
                    new_v = dict_clean_up(value, d)
                    val_list.append(new_v)
                new_dict[k] = val_list
            else:
                new_dict[k] = v

    return new_dict


class SaftExport(models.Model):
    _name = 'saft.ao.file.export'
    _description = 'SAFT Export for Angola'

    name = fields.Char("Name", readonly=True, required=True)
    state = fields.Selection([
        ('draft', 'Rascunho'),
        ('valid', 'Validado'),
        ('sent', 'Enviado')
    ],"State", default="draft")
    user_id = fields.Many2one('res.users', string="User", readonly=True)
    data = fields.Binary('File', readonly=True)
    content_xml = fields.Text(string="Text", readonly=True)
    date_from = fields.Date(string="Date From", required=True, readonly=True)
    date_to = fields.Date(string="Date To", required=True, readonly=True)
    company_id = fields.Many2one("res.company", required=True, string="Company", readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    audit_file_version = fields.Char(string="Audit File Version", size=10, required=True, readonly=True,
                                     help="Ficheiro de auditoria informática")
    tax_account_Basis = fields.Selection(string="Document Type",
                                         selection=[('I', 'Contablidade integrada com facturação'),
                                                    ('C', 'Contablidade'),
                                                    ('F', 'Facturação'),
                                                    # ('P', 'Facturação parcial'),
                                                    ('R', 'Recibos'),
                                                    ('S', 'Autofacturação'),
                                                    ('A', 'Aquisição de bens e serviços'),
                                                    ('Q', 'Aquisição de bens e serviços integrada com a facturação')],
                                         help="Tipos de Documentos, na exportação do SAFT", required=True,
                                         readonly=True,
                                         default="I")
    fiscal_year = fields.Integer(string="Fiscal Year", required=True, readonly=True)
    product_company_tax_id = fields.Char(string="NIF", size=20, required=True, readonly=True,
                                         help="Identidade Fiscal da Empresa Produtora do Software")
    software_validation_number = fields.Char(string="Software Number", required=True, readonly=True,
                                             help="Número de validação.Atríbuido à entidade produtora "
                                                  "do software")
    product_id = fields.Char(string="Product ID", required=True, size=255, readonly=True,
                             help="Nome da aplicação que gera o SAFT (AO).")
    product_version = fields.Char(string="Product Version", size=30, required=True, readonly=True,
                                  help="Deve ser indicada a versão da aplicação produtora do ficheiro.")
    header_comment = fields.Char(string="Header Comment", size=255, help="Comentários Adicionais")

    @api.constrains('company_id')
    def _check_company_access(self):
        for record in self:
            if record.company_id not in self.env.companies:
                raise AccessError("Não tem acesso aos ficheiros SAFT desta empresa.")

    def action_validate(self):
        module_path = os.path.dirname(os.path.abspath(__file__))
        module_root = os.path.dirname(module_path)
        xsd_file = os.path.join(module_root, 'data', 'SAFTAO1.01_01.xsd')

        result = valid_xml.valid_xml_with_agt_xsd(self.content_xml, xsd_file)
        if isinstance(result, str):
            raise ValidationError(result)
        self.state = 'valid'

    def action_download(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/download/saft_ao_file/%s' % (self.id),
            'target': 'new',
        }
