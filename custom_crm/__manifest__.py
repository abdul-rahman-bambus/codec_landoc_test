{
    'name': 'Custom CRM',
    'version': '18.0',
    'category': 'Sales',
    'active': True,
    'summary': 'CRM Customization',
    'author': 'Bambus Technologies LLP',
    'sequence': '1',
    'website': 'https://bambustechnologies.in/',
    'depends': [
        'base', 'sale', 'crm', 'partner_city_m2o', 'sale_management', 'account', 'custom_landoc',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'data': [
        # ---------- security ----------------#
        # 'security/crm_security.xml',
        'security/ir.model.access.csv',
        # ---------- data ----------------#
        'data/account_analytic_data.xml',
        'data/ir_sequence_common.xml',
        # ---------- views ----------------#
        'views/crm_lead.xml',
        'views/checklist_input.xml',
        'views/hr_employee.xml',
        'views/account_move_views.xml',
        'views/res_partner.xml',
        # ---------- wizard ----------------#
        'wizard/checklist_tracking.xml',
        'wizard/content_checklists_from_wiz.xml',
        'wizard/crm_lead_to_opportunity_views.xml',
        'wizard/legal_service_process.xml',
    ],
    'description': """
    """,
    'demo_xml': [],
    'license': 'OPL-1',
    "images": ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
