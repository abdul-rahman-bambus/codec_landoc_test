{
    'name': 'CRM Ticket Expenses',
    'version': '1.0',
    'category': 'CRM',
    'summary': 'Link employee expenses to CRM Leads (Tickets)',
    'depends': ['base', 'crm', 'custom_crm', 'hr_expense'],
    'data': [
        'views/crm_lead_views.xml',
        #'views/hr_expense_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': False,
}
