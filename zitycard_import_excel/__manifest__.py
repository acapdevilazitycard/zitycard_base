{
    'name': 'Zitycard Importar archivos excel',
    'version': '18.0.0.1',
    'summary': 'Zitycard Importar archivos excel mediante acciones planificadas',
    'description': """
        Zitycard Importar archivos excel
        ================================
        Zitycard Importar archivos excel mediante acciones planificadas
    """,
    'category': 'Others',
    'author': 'Zitycard',
    'website': 'https://www.zitycard.com',
    'depends': [
        'helpdesk',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/import_csv_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3'
}
