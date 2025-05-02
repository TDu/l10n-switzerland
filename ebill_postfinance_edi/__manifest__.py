# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "eBill Postfinance EDI",
    "summary": """Postfinance eBill integration with EDI framework""",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Camptocamp,Odoo Community Association (OCA)",
    "maintainers": ["TDu"],
    "website": "https://github.com/OCA/l10n-switzerland",
    "depends": [
        "account",
        # "account_invoice_export",
        # "base_ebill_payment_contract",
        "l10n_ch",
        "sale", # Could the base module do without ?
        "edi_oca",
    ],
    "external_dependencies": {
        "python": [
            "zeep",
            "ebilling_postfinance",
        ]
    },
    "data": [
        "data/edi_backend.xml",
        "security/ir.model.access.csv",
        "views/edi_backend_views.xml",
        "views/ebill_postfinance_service.xml",
    ],
}
