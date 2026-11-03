{
    'name': 'University Student Management',
    'version': '17.0.1.0.0',
    'category': 'Education',
    'summary': 'Student management for universities',
    'description': """
        University Student Management System.
        Manage students, personal information,
        academic records and enrollment.
    """,
    'author': 'Carlos Capemba Ferraz',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/student_views.xml',
    ],
    'installable': True,
    'application': True,
}