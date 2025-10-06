{
    "name": "Trocar O Idioma",
    "version": "15.0.1.0.0",
    "category": "Tools",
    "summary": "Troca idioma pelo systray com bandeiras",
    "depends": ["base", "web", "sale", "sale_management"],
    "data": [
        "views/language_switcher_templates.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "change_language/static/src/js/language_switcher.js",
        ],
    },
    "installable": True,
    "application": False,
}
