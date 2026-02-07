{
    'name': 'Report Preview in New Tab',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Open PDF reports in a new tab instead of downloading',
    'author': 'Agile Consulting',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'report_preview_inline/static/src/js/tools.esm.js',
            'report_preview_inline/static/src/js/report_preview.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
