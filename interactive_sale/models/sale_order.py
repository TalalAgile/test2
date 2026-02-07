# -*- coding: utf-8 -*--

from odoo import _, api, fields, models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "product.catalog.mixin"]

    def action_add_from_catalog(self):
        """Open the product catalog to add products to the sale order."""
        self.ensure_one()
        kanban_view_id = self.env.ref("product.product_view_kanban_catalog").id
        search_view_id = self.env.ref("product.product_view_search_catalog").id

        return {
            "type": "ir.actions.act_window",
            "name": _("Products"),
            "res_model": "product.product",
            "views": [(kanban_view_id, "kanban"), (False, "form")],
            "search_view_id": [search_view_id, "search"],
            "domain": [("sale_ok", "=", True)],
            "context": {
                "product_catalog_order_id": self.id,
                "product_catalog_order_model": self._name,
                "product_catalog_currency_id": self.currency_id.id,
                "order_id": self.id,
            },
            "target": "current",
        }

    def _default_order_line_values(self, child_field=False):
        return {
            "product_uom_qty": 0,
        }

    def _get_product_catalog_order_data(self, products, **kwargs):
        res = super()._get_product_catalog_order_data(products, **kwargs)
        for product in products:
            res[product.id]["price"] = product.list_price
            if self.pricelist_id:
                res[product.id]["price"] = self.pricelist_id._get_product_price(
                    product, 1.0, currency=self.currency_id
                )
        return res

    def _get_product_catalog_record_lines(self, product_ids, **kwargs):
        grouped_lines = {
            product: self.env["sale.order.line"]
            for product in self.env["product.product"].browse(product_ids)
        }
        for line in self.order_line:
            if line.product_id.id in product_ids:
                grouped_lines[line.product_id] |= line
        return grouped_lines

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        lines = self.order_line.filtered(lambda l: l.product_id.id == product_id)
        product = self.env["product.product"].browse(product_id)
        if lines:
            if quantity == 0:
                lines.unlink()
            else:
                lines[0].write({"product_uom_qty": quantity})
        elif quantity > 0:
            vals = {
                "order_id": self.id,
                "product_id": product_id,
                "product_uom_qty": quantity,
            }
            if self.pricelist_id:
                vals["price_unit"] = self.pricelist_id._get_product_price(
                    product, quantity, currency=self.currency_id
                )
            self.env["sale.order.line"].create(vals)

        if self.pricelist_id:
            return self.pricelist_id._get_product_price(
                product, quantity, currency=self.currency_id
            )
        return product.list_price


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _get_product_catalog_lines_data(self, **kwargs):
        """ Return data for the catalog view, handling empty recordsets. """
        product = self[0].product_id if self else self.env['product.product'].browse(kwargs.get('product_id'))
        
        qty = sum(self.mapped("product_uom_qty")) if self else 0.0
        price = 0.0
        
        if product:
            price = product.list_price
            order = self[0].order_id if self else self.env['sale.order'].browse(kwargs.get('order_id'))
            if order and order.pricelist_id:
                price = order.pricelist_id._get_product_price(
                    product, 1.0, currency=order.currency_id
                )

        return {
            "quantity": qty,
            "price": price,
            "readOnly": False,
            "uomDisplayName": product.uom_id.display_name if product else "",
        }
