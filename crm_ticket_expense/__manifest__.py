{
    'name': 'CRM Ticket Expenses',
    'version': '1.0',
    'category': 'CRM',
    'summary': 'Link employee expenses to CRM Leads (Tickets)',
    'depends': ['base', 'crm', 'hr_expense', 'custom_crm'],
    'data': [
        'views/crm_lead_views.xml',
        #'views/hr_expense_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
