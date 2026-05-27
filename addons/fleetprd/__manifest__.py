{
    'name': 'Fleet Management',
    'version': '15.0.1.0.0',
    'category': 'Fleet',
    'summary': 'Gestão Completa de Frota com Contratos, Manutenção e Análise de Custos',
    'description': """
        Módulo de Gestão de Frota Avançada para Odoo 15:
        - Gestão de contratos (leasing, seguro, aluguer)
        - Manutenção preventiva baseada em KM/Tempo
        - Controlo de odómetro e consumos
        - Análise de custos por veículo/motorista
        - Alertas e notificações automáticas
    """,
    'author': 'Carlos Ferraz, OLUALINET',
    'website': 'https://',
    'depends': ['base', 'fleet', 'mail'],
    'data': [
        'security/fleet_security.xml',
        'security/ir.model.access.csv',
        'data/fleet_sequence.xml',
        'data/cron_job.xml',
        # Caminho dos Reports
        'reports/contract_report.xml',
        'reports/contract_report_template.xml',
        'reports/service_report.xml',
        'reports/service_report_template.xml',
        'reports/vehicle_report.xml',
        'reports/vehicle_report_template.xml',
        'reports/fleet_cost_dashboard_report.xml',
        'reports/fleet_cost_dashboard_report_template.xml',
        # Fim
        'views/fleet_contract_view.xml',
        'views/fleet_service_view.xml',
        'views/fleet_vehicle_view.xml',
        'views/fleet_cost_analysis_view.xml',
        'views/driver_view.xml',
        'views/fleet_location_view.xml',

    ],

    'assets': {
        'web.assets_backend': [

            'fleetprd/static/src/css/style.css',
            'fleetprd/static/src/js/fleet_button_text.js',
            'fleetprd/static/src/js/fleet_cost_dashboard_pdf.js',
            'fleetprd/static/src/js/fleet_map.js',
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
            'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
        ],
    },

    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
