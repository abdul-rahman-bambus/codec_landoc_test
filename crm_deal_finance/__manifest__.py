
{
    'name': 'CRM Deal Finance',
    'version': '1.0.0',
    'category': 'CRM',
    'summary': 'Execute accounting operations directly from Opportunity',
    'depends': ['crm','sale','sale_crm','account','custom_crm','analytic','hr_expense'],
    'data': [
        'security/ir.model.access.csv',
        'views/deal_expense_views.xml',
        'views/deal_finance_wizard.xml',
        'views/crm_lead_view.xml',
    ],
    'installable': True,
}
