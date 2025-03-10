{
    'name': 'CRM - Transfer Database',
    'version': "17.0.1.0.0",
    'category': 'Personalizations',
    'author': 'Zitycard',
    'depends': [
        'crm',
        'account',
        'hr_attendance',
        'hr_holidays',
        'helpdesk',
        'documents',
        'sale_project',
        'industry_fsm_sale',
        'industry_fsm_report',
        'sale_subscription',
        'hr_expense',
        'website_sale_stock',
        'website_appointment_sale',
        'website_blog',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizards/crm_transfer_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto-install': False,
    'license': 'OPL-1',
}