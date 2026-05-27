from odoo import api, fields, models, tools


class FleetCostAnalysis(models.Model):
    _name = 'fleet.cost.analysis'
    _description = 'Análise de Custos da Frota'
    _auto = False
    _rec_name = 'vehicle_id'
    _date_name = 'date'

    date = fields.Date(string='Data', readonly=True)
    cost_type = fields.Selection([
        ('service', 'Serviço'),
        ('contract', 'Contrato')
    ], string='Tipo de Custo', readonly=True)

    service_type = fields.Char(string='Tipo de Serviço', readonly=True)

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Veículo',
        readonly=True
    )

    driver_id = fields.Many2one(
        'res.partner',
        string='Motorista',
        readonly=True
    )

    contract_id = fields.Many2one(
        'fleet.contract',
        string='Contrato',
        readonly=True
    )

    cost = fields.Monetary(
        string='Custo',
        readonly=True,
        currency_field='currency_id'
    )

    currency_id = fields.Many2one(
        'res.currency',
        string='Moeda',
        readonly=True
    )

    year = fields.Integer(string='Ano', readonly=True)
    month = fields.Integer(string='Mês', readonly=True)

    def action_print_dashboard_pdf(self):
        domain = self.env.context.get('active_domain')
        active_ids = self.env.context.get('active_ids')

        if domain:
            records = self.search(domain)
        elif active_ids:
            records = self.browse(active_ids)
        else:
            records = self.search([])

        return self.env.ref('fleetprd.report_fleet_cost_dashboard').report_action(records)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        self.env.cr.execute("""
            CREATE OR REPLACE VIEW fleet_cost_analysis AS (

                -- SERVIÇOS
                SELECT
                    ROW_NUMBER() OVER() AS id,

                    s.service_date AS date,

                    'service' AS cost_type,

                    s.service_type AS service_type,

                    s.vehicle_id AS vehicle_id,

                    s.driver_id AS driver_id,

                    NULL::INTEGER AS contract_id,

                    s.amount AS cost,

                    s.currency_id AS currency_id,

                    EXTRACT(YEAR FROM s.service_date)::INTEGER AS year,

                    EXTRACT(MONTH FROM s.service_date)::INTEGER AS month

                FROM fleet_service s
                WHERE s.state = 'completed'

                UNION ALL

                -- CONTRATOS
                SELECT
                    ROW_NUMBER() OVER() + 100000 AS id,

                    c.date_start AS date,

                    'contract' AS cost_type,

                    c.contract_type AS service_type,

                    c.vehicle_id AS vehicle_id,

                    NULL::INTEGER AS driver_id,

                    c.id AS contract_id,

                    c.monthly_cost AS cost,

                    c.currency_id AS currency_id,

                    EXTRACT(YEAR FROM c.date_start)::INTEGER AS year,

                    EXTRACT(MONTH FROM c.date_start)::INTEGER AS month

                FROM fleet_contract c
                WHERE c.state = 'active'
            )
        """)
