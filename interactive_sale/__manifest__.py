{
    "name": "Interactive Sale (Test2)",
    "version": "1.0",
    "summary": "Add items to Sale Order viaz Catalog",
    "description": """
        Adds an 'Add to Catalog' button on the Sale Order form.
        Allows adding items to the sale order using the product catalog view.
    """,
    "author": "Agile Consulting",
    "category": "Sales",
    "depends": ["sale", "product", "web"],
    "data": [
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}
