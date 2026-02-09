from odoo import models, fields, api

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def _get_dynamic_ingredients(self):
        self.ensure_one()
        ingredients = {} # {product.product record: qty}
        
        # Odoo 19: Selected attributes are in attribute_value_ids (product.template.attribute.value)
        # We map them to product.attribute.value (PAV)
        selected_pavs = self.attribute_value_ids.mapped('product_attribute_value_id')
        
        # Search for rules triggered by any of the selected attribute values
        domain = [('attribute_value_id', 'in', selected_pavs.ids)]
        all_rules = self.env['pos.attribute.deduction'].search(domain)
        
        for val in selected_pavs:
            rules = all_rules.filtered(lambda r: r.attribute_value_id == val)
            
            # Filter for this product specific OR global
            product_rules = rules.filtered(lambda r: self.product_id.product_tmpl_id in r.product_tmpl_ids)
            global_rules = rules.filtered(lambda r: not r.product_tmpl_ids)
            
            # Use product specific if available, otherwise global
            active_rules = product_rules or global_rules
            
            for deduction in active_rules:
                qty_to_add = 0
                if not deduction.deduction_line_ids:
                    pass
                
                # Look for matching condition (e.g. Size matches)
                match = deduction.deduction_line_ids.filtered(lambda l: l.condition_value_id in selected_pavs)
                if match:
                    qty_to_add = sum(match.mapped('quantity'))
                
                if qty_to_add > 0:
                    ingredients[deduction.product_id] = ingredients.get(deduction.product_id, 0) + qty_to_add
                    
        return ingredients

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def _create_move_from_pos_order_lines(self, lines):
        """
        Odoo 19 hook for creating POS stock moves.
        We inject dynamic ingredient moves here.
        """
        self.ensure_one()
        
        # Standard Odoo 19 behavior
        super()._create_move_from_pos_order_lines(lines)
        
        # Dynamic Kit logic
        dynamic_kit_lines = lines.filtered(lambda l: l.product_id.is_dynamic_kit)
        if not dynamic_kit_lines:
            return

        extra_move_vals = []
        for line in dynamic_kit_lines:
            ingredients = line._get_dynamic_ingredients()
            for ingredient, qty in ingredients.items():
                if not qty:
                    continue
                    
                total_qty = qty * abs(line.qty)
                
                # Create move values for the ingredient
                extra_move_vals.append({
                    'name': f"{line.name} (Ingredient: {ingredient.name})",
                    'product_id': ingredient.id,
                    'product_uom_qty': total_qty,
                    'product_uom': ingredient.uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'picking_id': self.id,
                    'picking_type_id': self.picking_type_id.id,
                    'company_id': self.company_id.id,
                    'state': 'draft',
                })

        if extra_move_vals:
            extra_moves = self.env['stock.move'].create(extra_move_vals)
            confirmed_extra_moves = extra_moves._action_confirm()
            confirmed_extra_moves.picked = True

