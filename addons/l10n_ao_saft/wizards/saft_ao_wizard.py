from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from dicttoxml2 import dicttoxml
from xml.dom.minidom import parseString
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from decimal import Decimal

# Ticblac Solution

def is_empty(value):
    """Verifica se um valor é considerado 'vazio' para remoção."""
    if value is None:
        return True
    # if isinstance(value, bool):
    #     return not value  # Remove se for False
    if isinstance(value, str):
        return len(value.strip()) == 0
    if isinstance(value, (dict, list, tuple)):
        return len(value) == 0
    return False  # Não remove números, objetos, etc.


def clean_dict(data):
    """Limpa o dicionário recursivamente, removendo campos vazios e tuplos desnecessários."""
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            # Processa valores que são dicionários
            if isinstance(value, dict):
                processed = clean_dict(value)
                if not is_empty(processed):
                    cleaned[key] = processed

            # Processa valores que são listas
            elif isinstance(value, list):
                processed_list = []
                for item in value:
                    # Caso especial: item é um tuplo (ex: invoices)
                    if isinstance(item, tuple):
                        # Processa cada elemento do tuplo e remove vazios
                        processed_elements = []
                        for e in item:
                            processed_e = clean_dict(e) if isinstance(e, dict) else e
                            if not is_empty(processed_e):
                                processed_elements.append(processed_e)

                        # Se o tuplo processado tiver elementos, adiciona à lista
                        if processed_elements:
                            # Se houver apenas 1 elemento, desempacota (remove o tuplo)
                            if len(processed_elements) == 1:
                                processed_list.append(processed_elements[0])
                            else:
                                processed_list.append(tuple(processed_elements))

                    # Caso geral: item não é tuplo
                    else:
                        processed_item = clean_dict(item) if isinstance(item, dict) else item
                        if isinstance(processed_item, dict):
                            if not is_empty(processed_item):
                                processed_list.append(processed_item)
                        else:
                            if not is_empty(item):
                                processed_list.append(item)

                # Adiciona a lista processada apenas se não estiver vazia
                if processed_list:
                    cleaned[key] = processed_list

            # Processa valores primitivos (strings, números, booleanos, etc.)
            else:
                if not is_empty(value):
                    cleaned[key] = value

        return cleaned

    # Processa listas fora de dicionários (caso raro)
    elif isinstance(data, list):
        return [clean_dict(item) for item in data if not is_empty(item)]

    # Retorna valores não dicionários/listas diretamente
    else:
        return data

months = {
    1: 'Janeiro',
    2: 'Fevereiro',
    3: 'Março',
    4: 'Abril',
    5: 'Maio',
    6: 'Junho',
    7: 'Julho',
    8: 'Agosto',
    9: 'Setembro',
    10: 'Outubro',
    11: 'Novembro',
    12: 'Dezembro'
}
file_types = [
    # ('I', 'Contablidade integrada com a facturação'),
    # ('C', 'Contabilidade'),
    ('F', 'Facturação'),
    # ('P', 'Facturação Parcial'),
    ('R', 'Recibos'),
    # ('S', 'Auto-Facturação'),
    # ('A', 'Aquisição de bens e serviços'),
    # ('Q', 'Aquisição de bens e serviços integrada com a facturação')
]


class L10nAOSaftWizard(models.TransientModel):
    _name = "saft.ao.export.wizard"
    _description = "Estes modelo representa o wizard de exportação do ficheiro SAFT_AO"

    @api.model
    def _default_company(self):
        return self.env.company.id

    @api.model
    def _get_last_day(self):
        today = datetime.now()
        first_day = today.replace(day=1)
        last_day = (first_day + relativedelta(months=1, days=-1))
        return last_day

    company_id = fields.Many2one(comodel_name="res.company", string="Companhia", required=True,
                                 default=_default_company, )
    type = fields.Selection(string="File Type", selection=file_types, help="Tipo de ficheiro")
    date_to = fields.Date("Date End", default=_get_last_day)
    date_from = fields.Date("Date Start", default=fields.Date.today().replace(day=1))
    comments = fields.Char("Comment")

    @api.constrains('date_to', 'date_from')
    def check_dates(self):
        if self.date_from > self.date_to:
            raise ValidationError('A data inicial deve ser menor que a data final.')
        if self.date_from.month != self.date_to.month:
            raise ValidationError('A data inicial e a data final devem ser do mesmo mês.\n'
                                  'O SAFT AO deve ser mensal.')

    def get_pos_saft(self, invoice_saft):
        return invoice_saft

    def get_pos_partners(self):
        return self.env["res.partner"]

    def get_pos_products(self):
        return self.env['product.product']

    def get_pos_taxes(self):
        return self.env['account.tax']

    def check_item(self, parent):
        if parent == "Supplier":
            return "Supplier"
        if parent == "Product":
            return "Product"
        if parent == "GeneralLedgerAccounts":
            return "Account"
        if parent == "TaxTable":
            return "TaxTable"

    def get_saft_xml(self):

        if not self.company_id.vat:
            raise ValidationError(_("Não é possível gerar dados SAFT sem o NIF da empresa!"))
        if not self.company_id.company_registry:
            raise ValidationError(_("Não é possível gerar dados SAFT sem o nº de Registro Comercial da Empresa!"))

        header = {
            "AuditFileVersion": self.company_id.audit_file_version,
            "CompanyID": str(self.company_id.company_registry)[0:49] if self.company_id.company_registry else " ",
            "TaxRegistrationNumber": self.company_id.vat if self.company_id.vat else "",
            "TaxAccountingBasis": self.type,
            "CompanyName": self.company_id.name,
            "BusinessName": self.company_id.partner_id.industry_id.name if self.company_id.partner_id.industry_id.name
            else self.company_id.name,
            "CompanyAddress": {
                # "BuildingNumber": "","
                "StreetName": self.company_id.partner_id.street if self.company_id.partner_id.street else "",
                "AddressDetail": str(self.company_id.partner_id.contact_address)[0:80],
                "City": self.company_id.partner_id.city,
                "PostalCode": self.company_id.partner_id.zip if self.company_id.partner_id.zip else "",
                "Province": self.company_id.partner_id.state_id.name if self.company_id.partner_id.state_id.name else "Desconhecido",
                "Country": str(self.company_id.partner_id.country_id.code)[
                           0:2] if self.company_id.partner_id.country_id.code else "Desconhecido"
            },
            "FiscalYear": int(fields.Date.to_string(self.date_to)[0:4]),
            "StartDate": fields.Date.to_string(self.date_from),
            "EndDate": fields.Date.to_string(self.date_to),
            "CurrencyCode": self.company_id.currency_id.name,
            "DateCreated": fields.Date.to_string(fields.Date.today()),
            "TaxEntity": "Global",
            "ProductCompanyTaxID": self.company_id.product_company_tax_id,
            "SoftwareValidationNumber": self.company_id.agt_cert_number,
            "ProductID": self.company_id.agt_product_name,
            "ProductVersion": self.company_id.agt_product_version or "18.19.20",
            "HeaderComment": self.comments,
            "Telephone": self.company_id.phone and self.company_id.phone[0:19] or '',
            # "Fax": "",
            "Email": self.company_id.email,
            "Website": self.company_id.website if self.company_id.website else "Desconhecido",
        }

        saft_dict = {
            "Header": header,
            "MasterFiles": "",
            "GeneralLedgerEntries": "",
            "SourceDocuments": "",
        }

        source_documents = {

            "SalesInvoices": "",
            "MovementOfGoods": "",
            "WorkingDocuments": "",
            "Payments": "",
            "PurchaseInvoices": "",
        }

        master_files = {
            "GeneralLedgerAccounts": "",
            "Customer": "",
            "Supplier": "",
            "Product": "",
            "TaxTable": "",
        }

        partners = self.env["res.partner"]
        suppliers = self.env["res.partner"]
        taxes = self.env["account.tax"]
        journals = self.env["account.journal"]
        products = self.env["product.product"]

        invoices = self.env["account.move"].search(
            [("invoice_date", ">=", fields.Date.to_string(self.date_from)),
             ("invoice_date", "<=", fields.Date.to_string(self.date_to)),
             # ("system_entry_date", "!=", None),
             ("state", "in", ["posted"])
             ], order="system_entry_date asc")

        # st_movments = self.env["stock.picking"].search(
        #     [("picking_date", ">=", fields.Date.to_string(self.date_from)), ("system_entry_date", "!=", None),
        #      ("picking_date", "<=", fields.Date.to_string(self.date_to)), ("state", "in", ["done"]),
        #      ("picking_type_code", "in", ["outgoing", "incoming"])], order="system_entry_date asc")

        if self.type in ["A"]:
            invoices = self.env["account.move"].search(
                [("invoice_date", ">=", fields.Date.to_string(self.date_from)),
                 ("invoice_date", "<=", fields.Date.to_string(self.date_to)),
                 ("system_entry_date", "!=", None),
                 ("move_type", "in", ["in_invoice"])
                 ], order="system_entry_date asc")
            accounts = self.env["account.account"].search([])
            account_account = accounts.with_context(date_from=self.date_from,
                                                    date_to=self.date_to)
            partners |= invoices.mapped("partner_id")
            master_files["Customer"] = partners.get_saft_data().get("Customer")
            invoices_lines_taxes = invoices.mapped("invoice_line_ids")
            taxes |= invoices_lines_taxes.mapped("tax_ids")
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")
            master_files["GeneralLedgerAccounts"] = account_account.get_saft_data().get("GeneralLedgerAccounts")
            master_files["Supplier"] = partners.get_saft_data().get("Supplier")
            source_documents["PurchaseInvoices"] = invoices.get_supplier_saft_data().get("PurchaseInvoices")
            saft_dict['SourceDocuments'] = source_documents
            [source_documents.pop(keys) for keys in
             ["SalesInvoices", "Payments", "MovementOfGoods", "WorkingDocuments"]]
            master_files.pop("Customer")
            master_files.pop("Product")
            saft_dict.pop("GeneralLedgerEntries")
            master_files.pop("GeneralLedgerAccounts")

            # saft_dict["SourceDocuments"]["Invoices"] = invoices.get_saft_data().get("Invoices")

        if self.type in ["R", "F"]:
            invoices = invoices.filtered(lambda r: r.move_type in ['out_invoice', 'out_refund'])
            partners |= invoices.mapped("partner_id")
            if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_pos'):
                value = self.get_pos_partners()
                partners |= self.get_pos_partners() if self.get_pos_partners() != None else self.env['res.partner']
            master_files["Customer"] = partners.get_saft_data().get("Customer")
            master_files["Product"] = products.get_saft_data().get("Product")
            invoices_taxes = invoices.mapped("invoice_line_ids")
            taxes |= invoices_taxes.mapped("tax_ids")
            taxes = taxes.filtered(lambda r: r.tax_type in ['IVA', 'IS', 'NS'] and r.tax_exigibility != "withholding")
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")

            if self.type in ["R"]:
                # payments = invoices.mapped('matched_payment_ids')
                # source_documents["Payments"] = payments.get_saft_data().get("Payments")

                master_files.pop("GeneralLedgerAccounts")
                master_files.pop("Supplier")
                saft_dict.pop("GeneralLedgerEntries")
                [source_documents.pop(keys) for keys in ["SalesInvoices", "MovementOfGoods", "WorkingDocuments"]]
                saft_dict["SourceDocuments"] = source_documents

        if self.type in ["F", "I", "Q"]:
            # sales = self.env["sale.order"].search(
            #     [("date", ">=", fields.Date.to_string(self.date_from)), ("system_entry_date", "!=", None),
            #      ("date", "<=", fields.Date.to_string(self.date_to)), ("state", "in", ["sale"]),
            #      ("type", "in", ["PP", "OR", "OU"])], order="system_entry_date asc")

            if self.type == "S":
                invoices = invoices.filtered(lambda r: r.journal_id.self_billing and r.move_type in ["in_invoice"] and
                                                       r.partner_id.self_billing_s)

            customer_invoices = invoices.filtered(lambda r: r.move_type in ["out_invoice", "out_refund"])
            supplier_invoices = invoices.filtered(lambda r: r.move_type in ["in_invoice", "in_refund"])
            partners |= customer_invoices.mapped("partner_id")
            suppliers |= supplier_invoices.mapped("partner_id")
            products |= invoices.mapped("invoice_line_ids.product_id")
            if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_pos'):
                products |= self.get_pos_products() if self.get_pos_products() != None else self.env['product.product']
            customer_taxes = customer_invoices.mapped("invoice_line_ids.tax_ids")
            supplier_taxes = supplier_invoices.mapped("invoice_line_ids.tax_ids")
            customer_taxes = customer_taxes.filtered(
                lambda r: r.tax_type in ['IVA', 'IS', 'NS'] and r.tax_exigibility != "withholding")
            supplier_taxes = supplier_taxes.filtered(
                lambda r: r.tax_type in ['IVA', 'IS', 'NS'] and r.tax_exigibility != "withholding")

            if self.type == "Q":
                master_files.pop("GeneralLedgerAccounts")
                saft_dict.pop("GeneralLedgerEntries")
                source_documents["PurchaseInvoices"] = invoices.get_supplier_Saft_data().get("PurchaseInvoices")
                taxes = supplier_taxes

            if self.type == "S":
                invoices = invoices.filtered(lambda r: r.journal_id.self_billing and r.type in ["in_invoice"] and
                                                       r.partner_id.self_billing_s)
            if self.type in ["F"]:
                # st_movment_outs = st_movments.filtered(lambda r: r.picking_type_code == "outgoing")
                # payments = invoices.mapped('matched_payment_ids')

                source_documents["SalesInvoices"] = invoices.get_saft_data().get("SalesInvoices")
                # source_documents["WorkingDocuments"] = sales.get_saft_data().get("WorkingDocuments")
                # source_documents["MovementOfGoods"] = st_movment_outs.get_saft_data().get("MovementOfGoods")
                # source_documents["Payments"] = payments.get_saft_data().get("Payments")

                if not self.env['ir.config_parameter'].sudo().get_param('dont_validate_pos'):
                    source_documents["SalesInvoices"] = self.get_pos_saft(source_documents["SalesInvoices"])
                [source_documents.pop(keys) for keys in ["PurchaseInvoices"]]
                taxes |= self.get_pos_taxes() if self.get_pos_taxes() != None else self.env['account.tax']
                taxes |= customer_taxes
                if source_documents["SalesInvoices"]["NumberOfEntries"] == 0:
                    raise UserError(
                        "Não existem faturas registadas para o período selecionado para extração do ficheiro SAFT.\n"
                        " Por favor, verifique as entradas deste mês.")
                saft_dict["SourceDocuments"] = source_documents

            master_files["Product"] = products.get_saft_data().get("Product")
            # master_files["Supplier"] = suppliers.get_saft_data().get("Supplier")
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")

            saft_dict["SourceDocuments"] = source_documents
            if self.type == "F":
                master_files.pop("GeneralLedgerAccounts")
                saft_dict.pop("GeneralLedgerEntries")
                master_files.pop("Supplier")

        if self.type in ["C", "I"]:
            accounts = self.env["account.account"].search([])
            account_account = accounts.with_context(date_from=self.date_from,
                                                    date_to=self.date_to)

            partners |= account_account.get_saft_data().get("customers")
            partners |= account_account.get_saft_data().get("suppliers")
            taxes |= account_account.get_saft_data().get("taxes")
            journals |= account_account.get_saft_data().get("journals")

            master_files["Customer"] = partners.get_saft_data().get("Customer")
            master_files["Supplier"] = partners.get_saft_data().get("Supplier")
            master_files["TaxTable"] = taxes.get_saft_data().get("TaxTable")
            master_files["GeneralLedgerAccounts"] = {
                "Account": account_account.get_saft_data().get("GeneralLedgerAccounts")}
            saft_dict["GeneralLedgerEntries"] = journals.with_context(
                date_from=self.date_from,
                date_to=self.date_to
            ).get_saft_data().get("GeneralLedgerEntries")

        saft_dict["MasterFiles"] = master_files

        data_saft_ao = clean_dict(saft_dict)
        print(data_saft_ao)

        saft_xml = dicttoxml(
            data_saft_ao,
            custom_root="AuditFile",
            attr_type=False,
            item_func=self.check_item,
            fold_list=False
        )

        dom = str(saft_xml, 'utf-8')
        dom = parseString(dom).toprettyxml()

        saft_file_data = {

            "name": "SAFT_AO_XML_%s_%s_%s" % (
                self.type, fields.Date.to_string(self.date_from)[0:4],
                months[self.date_to.month].upper()
            ),
            "audit_file_version": self.company_id.audit_file_version,
            "tax_account_Basis": self.type,
            "company_id": self.company_id.id,
            "fiscal_year": int(fields.Date.to_string(fields.Date.today())[0:4]),
            "date_from": fields.Date.to_string(self.date_from),
            "date_to": fields.Date.to_string(self.date_to),
            "product_company_tax_id": self.company_id.product_company_tax_id,
            "software_validation_number": self.company_id.agt_cert_number,
            "product_id": self.company_id.agt_product_name,
            "product_version": self.company_id.agt_product_version or '18.19.20',
            "header_comment": self.comments,
            "content_xml": dom.replace("–", "-").replace("<AuditFile>",
                                                         '<AuditFile xmlns="urn:OECD:StandardAuditFile-Tax:AO_1.01_01" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">').replace(
                '<?xml version="1.0" ?>', '<?xml version="1.0" encoding="UTF-8" ?>'),
            "user_id": self.env.user.id,
        }
        action = self.create_and_return_action(saft_file_data)
        return action

    @api.model
    def create_and_return_action(self, saft_file_data):
        try:
            # Criar o registro de exportação SAFT
            saft_file = self.env["saft.ao.file.export"].create(saft_file_data)

            # Obter a ação para exibição do arquivo
            action_ref = self.env.ref('l10n_ao_saft.saft_ao_file_action', raise_if_not_found=False)
            if not action_ref:
                raise ValidationError("A ação para o arquivo SAFT não foi encontrada.")

            # Obter a visão do formulário para a exportação
            view_ref = self.env.ref('l10n_ao_saft.saft_ao_file_export_view', raise_if_not_found=False)
            if not view_ref:
                raise ValidationError("A visão para exportação do arquivo SAFT não foi encontrada.")

            # Configurar a ação para exibir o arquivo
            action = action_ref.read()[0]
            action['views'] = [(view_ref.id, 'form')]
            action['res_id'] = saft_file.id

            return action
        except Exception as e:
            raise ValidationError(f"Ocorreu um erro ao criar o arquivo SAFT ou configurar a ação: {str(e)}")

