# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2025 TICBLAC SOLUTION Lda, Lda. All Rights Reserved
# http://www.ticblac.com.
{
    'name': 'Angola - RH',
    'version': '1.1',
    'summary': 'Angola - Recursos Humanos',
    'author': 'Ticblac Solution - Serviços, Lda',
    'category': 'Human Resources/Employees',
    'website': 'http://www.ticblac.com.',
    'depends': [
        'hr',
        'hr_recruitment',
        'timesheet_grid',
        'hr_timesheet',
        'hr_payroll',
        'l10n_ao_hr_payroll',
        'hr_holidays',
        'hr_attendance',
        'hr_work_entry_contract',
        'hr_appraisal',
        'hr_skills',
    ],
    'data': [
        'data/codes_deduction_data.xml',
        'data/codes_remuneration_data.xml',
        'data/contract_type.xml',
        # 'data/ir_sequence_data.xml',
        'data/mail_template.xml',
        'data/cron_data.xml',

        'security/security.xml',

        'menu/menu.xml',

        'views/res_company_view.xml',
        'views/parent_view.xml',
        'views/employee_view.xml',
        'views/contract_view.xml',
        'views/remuneration_view.xml',
        'views/holidays_view.xml',
        'views/salaryrule_view.xml',
        'views/schedule_view.xml',
        'views/payslip_view.xml',

        'wizard/wizard_salary_view.xml',
        'wizard/wizard_inss_view.xml',
        'wizard/wizard_irt_view.xml',
        # 'wizard/wizard_bank_view.xml',
        'wizard/wizard_employee_extract_view.xml',
        'wizard/wizard_contract_list_view.xml',
        'wizard/payroll_employee_wizard.xml',
        # 'wizard/wizard_indication.xml',
        # 'wizard/wizard_employee_external_jobs.xml',

        'report/reports.xml',
        # 'report/report_bank.xml',
        'report/report_inss.xml',
        'report/report_irt.xml',
        'report/report_salary.xml',
        'report/report_simple_payslip.xml',

        'report/report_employee_list.xml',
        # 'report/report_employee_list_department.xml',
        # 'report/report_work_declaration.xml',

        'report/report_irt_group_a.xml',
        'report/report_irt_group_bc.xml',
        'report/report_employee_extract.xml',
        # 'report/report_employee_contract_historic.xml',
        # 'report/report_leadership_development_plan.xml',
        # 'report/report_training_request.xml',
        'report/report_employee_contract_list.xml',
        'report/report_payslip.xml',
        # 'report/report_contract_determinado.xml',
        'report/history_contract.xml'

    ],
    'application': True,
    'auto_install': False,
    'installable': True,
    'license': 'OPL-1',
    'currency': 'AOA',
}
