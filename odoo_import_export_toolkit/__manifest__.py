# -*- coding: utf-8 -*-
{
    'name': 'Odoo Import/Export & Data Cleanup Toolkit',
    'version': '18.0.1.0.0',
    'summary': 'Import, export, and clean up your Odoo data with AI-powered validation.',
    'description': """
Odoo Import/Export & Data Cleanup Toolkit
=========================================

A comprehensive toolkit for importing, exporting, and cleaning up your Odoo data.

Features:
- Export jobs with CSV, XLSX, and JSON format support
- Import jobs with configurable field mapping
- Data cleanup rules (trim whitespace, remove duplicates, fix case, validate email, normalize phone, fill defaults)
- AI-powered data validation with suggestions

Powered by SoftaiDev.
""",
    'author': 'SoftaiDev',
    'website': 'https://softaidev.pages.dev',
    'category': 'Productivity/AI',
    'license': 'LGPL-3',
    'price': 39.99,
    'currency': 'USD',
    'depends': ['base', 'web', 'mail'],
    'application': True,
    'installable': True,
    'data': [
        'security/ir.model.access.csv',
        'views/iet_export_job_views.xml',
        'views/iet_import_job_views.xml',
        'views/iet_cleanup_rule_views.xml',
        'views/iet_data_validation_views.xml',
        'views/iet_menu.xml',
    ],
    'images': ['static/description/cover.png'],
}
