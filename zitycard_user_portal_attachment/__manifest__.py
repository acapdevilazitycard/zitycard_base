{
    'name': 'Zitycard Portal User documents',
    'version': '18.0.0.1',
    'summary': 'Zitycard Portal User documents',
    'description': """
        Zitycard Portal User documents
        ==============================
        Permite añadir documentos en los contactos para los usuarios de portal.
    """,
    'category': 'Website',
    'author': 'Zitycard',
    'website': 'https://www.zitycard.com',
    'depends': ['portal'],
    'data': [
        'views/documents_templates_portal.xml',
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3'
}
