import xmlrpc.client
import requests
import json
import time

VERSION = "1.0.3 - Smart Prefix Support"

# --- CONFIGURATION ---
URL = "https://talalagile-test2.odoo.com"
DB = "talalagile-test2-main-27890898"
USER = "admin"
PASS = "123"

TELEGRAM_TOKEN = "8219466246:AAHOrIP8rKksGqLfzIHDdfCz24X4W47xogM"
OPENAI_KEY = "" # Will be fetched from Odoo or provided

import base64

# --- ODOO TOOLS ---
def odoo_search_products(models, uid, db, pwd, query):
    ids = models.execute_kw(db, uid, pwd, 'product.product', 'search', [[['name', 'ilike', query]]], {'limit': 5})
    if not ids: return "No products found."
    prods = models.execute_kw(db, uid, pwd, 'product.product', 'read', [ids], {'fields': ['name', 'list_price']})
    return json.dumps(prods)

def odoo_get_product_details(models, uid, db, pwd, product_id):
    try:
        prod = models.execute_kw(db, uid, pwd, 'product.product', 'read', [int(product_id)], {'fields': ['name', 'list_price', 'qty_available', 'description_sale']})
        return json.dumps(prod)
    except:
        return "Error fetching product details."

def telegram_send_image(models, uid, db, pwd, product_id, chat_id, token):
    try:
        prod = models.execute_kw(db, uid, pwd, 'product.product', 'read', [int(product_id)], {'fields': ['image_1920']})
        if prod and prod[0].get('image_1920'):
            image_data = base64.b64decode(prod[0]['image_1920'])
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            files = {'photo': ('image.jpg', image_data)}
            requests.post(url, data={'chat_id': chat_id}, files=files)
            return "Image sent successfully."
        return "This product does not have an image."
    except Exception as e:
        return f"Error sending image: {e}"

def odoo_create_quotation(models, uid, db, pwd, lead_id, product_id, quantity, chat_id, token):
    try:
        # 1. Get Lead Info
        lead = models.execute_kw(db, uid, pwd, 'crm.lead', 'read', [int(lead_id)], {'fields': ['partner_id', 'contact_name', 'email_from']})[0]
        partner_id = lead.get('partner_id') and lead['partner_id'][0]
        
        # 2. If no partner, find or create one
        if not partner_id:
            partner_name = lead.get('contact_name') or f"Telegram Customer {chat_id}"
            existing_partners = models.execute_kw(db, uid, pwd, 'res.partner', 'search', [[['name', '=', partner_name]]])
            if existing_partners:
                partner_id = existing_partners[0]
            else:
                partner_id = models.execute_kw(db, uid, pwd, 'res.partner', 'create', [{'name': partner_name, 'email': lead.get('email_from')}])
            models.execute_kw(db, uid, pwd, 'crm.lead', 'write', [[int(lead_id)], {'partner_id': partner_id}])

        # 3. Create Sale Order
        so_vals = {
            'partner_id': partner_id,
            'opportunity_id': lead_id,
            'order_line': [(0, 0, {
                'product_id': int(product_id),
                'product_uom_qty': float(quantity),
            })]
        }
        so_id = models.execute_kw(db, uid, pwd, 'sale.order', 'create', [so_vals])
        so_name = models.execute_kw(db, uid, pwd, 'sale.order', 'read', [so_id], {'fields': ['name']})[0]['name']
        
        # 4. Generate PDF Report (Odoo 19 report service)
        # Using ir.actions.report to generate the PDF
        report_service = f"{URL}/report/pdf/sale.report_saleorder/{so_id}"
        # However, via XML-RPC we usually use 'render_qweb_pdf' or similar on ir.actions.report
        # In Odoo 19, the standard way via RPC is:
        result, format = models.execute_kw(db, uid, pwd, 'ir.actions.report', 'render_qweb_pdf', [['sale.report_saleorder'], [so_id]])
        
        if result:
            pdf_content = base64.b64decode(result)
            url = f"https://api.telegram.org/bot{token}/sendDocument"
            files = {'document': (f"{so_name}.pdf", pdf_content)}
            requests.post(url, data={'chat_id': chat_id, 'caption': f"Here is your quotation {so_name}"}, files=files)
            return f"Quotation {so_name} created and sent successfully."
        return "Quotation created but failed to generate PDF."
    except Exception as e:
        print(f"Error creating quotation: {e}", flush=True)
        return f"Error creating quotation: {str(e)}"

def transcribe_voice(file_id, token, api_key):
    try:
        # 1. Get File Path from Telegram
        get_file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        resp = requests.get(get_file_url)
        file_path = resp.json()['result']['file_path']
        
        # 2. Download File
        download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        audio_data = requests.get(download_url).content
        
        # 3. Transcribe with Whisper
        url = "https://api.openai.com/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {api_key}"}
        # Pass model as data, file as files
        data = {"model": "whisper-1"}
        files = {"file": ("voice.ogg", audio_data, "audio/ogg")}
        
        response = requests.post(url, headers=headers, data=data, files=files, timeout=35)
        if response.status_code != 200:
            print(f"Whisper Error: {response.status_code} - {response.text}")
            return ""
            
        transcription = response.json().get('text', "")
        return transcription
    except Exception as e:
        print(f"Transcription Error: {e}")
        return ""

def odoo_create_invoice(models, uid, db, pwd, order_ref, chat_id, telegram_token):
    """Delegate invoicing to the native Odoo 'AI Automation' mixin."""
    try:
        # Call the native Odoo method we just built
        result = models.execute_kw(db, uid, pwd, 'sale.order', 'action_ai_create_invoice_for_so', [], {
            'order_ref': order_ref,
            'chat_id': chat_id,
            'telegram_token': telegram_token
        })
        return result
    except Exception as e:
        return f"Native Invoicing Error: {str(e)}"

def odoo_validate_delivery(models, uid, db, pwd, so_id):
    try:
        # Find pickings for this SO
        pickings = models.execute_kw(db, uid, pwd, 'stock.picking', 'search_read', 
            [[['origin', 'ilike', str(so_id)]]], 
            {'fields': ['id', 'state', 'name']}) # Using ilike on origin which usually contains SO Name. Ideally query via sale_order link if possible in v19.
            
        # Better: Read SO's picking_ids
        so = models.execute_kw(db, uid, pwd, 'sale.order', 'read', [int(so_id)], {'fields': ['picking_ids', 'name']})[0]
        picking_ids = so.get('picking_ids', [])
        
        if not picking_ids: return f"No delivery orders found for {so['name']}."
        
        actions_taken = []
        for pid in picking_ids:
            pick = models.execute_kw(db, uid, pwd, 'stock.picking', 'read', [pid], {'fields': ['state', 'name']})[0]
            if pick['state'] in ['done', 'cancel']: continue
            
            # Simple "Make Done" logic: Set quantities on moves
            # Get moves
            moves = models.execute_kw(db, uid, pwd, 'stock.move', 'search_read', [[['picking_id', '=', pid]]], {'fields': ['id', 'product_uom_qty']})
            for move in moves:
                # Set quantity_done = reserved or uom_qty
                # In recent Odoo, we write to 'quantity' or 'quantity_done' on move.line or move
                # Simplest for "Verify" button behavior: call button_validate. 
                # If immediate transfer, it might just work.
                pass 

            # Try validating
            try:
                # This often triggers a wizard if not all qty are done. 
                # For automation, we can try 'action_set_quantities_to_reservation' first if available (v15+)
                # models.execute_kw(db, uid, pwd, 'stock.picking', 'action_set_quantities_to_reservation', [[pid]])
                models.execute_kw(db, uid, pwd, 'stock.picking', 'button_validate', [[pid]])
                actions_taken.append(f"Validated {pick['name']}")
            except Exception as e:
                actions_taken.append(f"Could not validate {pick['name']}: {e}")
                
        return "\n".join(actions_taken) if actions_taken else "All transfers already done."
    except Exception as e:
        return f"Error validating delivery: {str(e)}"

def odoo_register_payment(models, uid, db, pwd, invoice_ref, amount=None):
    """Delegate payment registration to the native Odoo 'AI Automation' mixin."""
    try:
        result = models.execute_kw(db, uid, pwd, 'account.move', 'action_ai_register_payment', [], {
            'invoice_ref': invoice_ref,
            'amount': amount
        })
        return result
    except Exception as e:
        return f"Native Payment Error: {str(e)}"

def odoo_get_stock_forecast(models, uid, db, pwd, product_id):
    try:
        fields = ['qty_available', 'virtual_available', 'incoming_qty', 'outgoing_qty', 'name']
        prod = models.execute_kw(db, uid, pwd, 'product.product', 'read', [int(product_id)], {'fields': fields})[0]
        return json.dumps(prod)
    except Exception as e:
        return f"Error fetching stock forecast: {str(e)}"

def odoo_get_my_leads(models, uid, db, pwd, chat_id):
    try:
        leads = models.execute_kw(db, uid, pwd, 'crm.lead', 'search_read', 
            [[['telegram_chat_id', '=', str(chat_id)]]], 
            {'fields': ['name', 'stage_id', 'probability', 'expected_revenue'], 'limit': 5})
        return json.dumps(leads)
    except Exception as e:
        return f"Error fetching leads: {str(e)}"

def odoo_update_lead_phone(models, uid, db, pwd, lead_id, phone):
    try:
        # Update Lead
        models.execute_kw(db, uid, pwd, 'crm.lead', 'write', [[int(lead_id)], {'phone': phone, 'mobile': phone}])
        # Update Partner if exists
        lead = models.execute_kw(db, uid, pwd, 'crm.lead', 'read', [int(lead_id)], {'fields': ['partner_id']})[0]
        if lead['partner_id']:
            models.execute_kw(db, uid, pwd, 'res.partner', 'write', [lead['partner_id'][0], {'phone': phone, 'mobile': phone}])
        return "Phone number updated successfully."
    except Exception as e:
        return f"Error updating phone: {str(e)}"

def odoo_get_lead_related_orders(models, uid, db, pwd, lead_id):
    try:
        orders = models.execute_kw(db, uid, pwd, 'sale.order', 'search_read', 
            [[['opportunity_id', '=', int(lead_id)]]], 
            {'fields': ['name', 'state', 'amount_total'], 'limit': 5})
        return json.dumps(orders)
    except Exception as e:
        return f"Error fetching related orders: {str(e)}"

def odoo_confirm_order(models, uid, db, pwd, so_id):
    try:
        models.execute_kw(db, uid, pwd, 'sale.order', 'action_confirm', [[int(so_id)]])
        return f"Sale Order {so_id} confirmed successfully."
    except Exception as e:
        return f"Error confirming order: {str(e)}"

def odoo_get_order_by_name(models, uid, db, pwd, order_name):
    try:
        search_name = str(order_name).strip()
        domain = [['name', 'ilike', search_name]]
        
        # Smart Search: Try variants (SO vs S), then numeric fallback
        if search_name.upper().startswith('SO'):
            alt_name = 'S' + search_name[2:]
            domain = ['|'] + domain + [['name', 'ilike', alt_name]]
        elif search_name.upper().startswith('S') and not search_name.upper().startswith('SO'):
            alt_name = 'SO' + search_name[1:]
            domain = ['|'] + domain + [['name', 'ilike', alt_name]]

        print(f"DEBUG: get_order_by_name searching for {search_name} with {domain}", flush=True)
        orders = models.execute_kw(db, uid, pwd, 'sale.order', 'search_read', 
            [domain], 
            {'fields': ['id', 'name', 'state', 'amount_total', 'invoice_ids'], 'limit': 1})
        print(f"DEBUG: get_order_by_name found {len(orders)} matches", flush=True)
            
        if not orders:
            import re
            digits = re.search(r'\d+$', search_name)
            if digits:
                num_search = f"%{digits.group()}"
                orders = models.execute_kw(db, uid, pwd, 'sale.order', 'search_read', 
                    [[['name', 'like', num_search]]], 
                    {'fields': ['id', 'name', 'state', 'amount_total', 'invoice_ids'], 'limit': 1})
        if not orders: return f"No order found matching '{order_name}'."
        order = orders[0]
        order['invoice_ids'] = order.get('invoice_ids', [])
        return json.dumps(order)
    except Exception as e:
        return f"Error fetching order: {str(e)}"

def odoo_get_my_orders(models, uid, db, pwd, chat_id):
    try:
        # Resolve partner from Lead or directly? Better to find partner via Lead associated with chat_id
        lead_ids = models.execute_kw(db, uid, pwd, 'crm.lead', 'search', [[['telegram_chat_id', '=', str(chat_id)]]])
        if not lead_ids: return "No customer found."
        lead = models.execute_kw(db, uid, pwd, 'crm.lead', 'read', [lead_ids[0]], {'fields': ['partner_id']})[0]
        partner_id = lead.get('partner_id') and lead['partner_id'][0]
        if not partner_id: return "No customer record linked."

        orders = models.execute_kw(db, uid, pwd, 'sale.order', 'search_read', 
            [[['partner_id', '=', partner_id]]], 
            {'fields': ['name', 'state', 'amount_total', 'date_order'], 'limit': 5, 'order': 'date_order desc'})
        if not orders: return "No recent orders found."
        return json.dumps(orders)
    except Exception as e:
        return f"Error fetching orders: {str(e)}"

# ==================== INVENTORY MODULE ====================

def odoo_transfer_stock(models, uid, db, pwd, product_id, from_location_id, to_location_id, quantity):
    """Transfer stock between warehouse locations"""
    try:
        picking_type = models.execute_kw(db, uid, pwd, 'stock.picking.type', 'search', 
            [[['code', '=', 'internal']]], {'limit': 1})
        if not picking_type: return "Internal transfer operation not configured."
        
        picking_vals = {
            'picking_type_id': picking_type[0],
            'location_id': int(from_location_id),
            'location_dest_id': int(to_location_id),
            'move_ids_without_package': [(0, 0, {
                'name': 'Internal Transfer',
                'product_id': int(product_id),
                'product_uom_qty': float(quantity),
                'product_uom': 1,
                'location_id': int(from_location_id),
                'location_dest_id': int(to_location_id),
            })]
        }
        
        picking_id = models.execute_kw(db, uid, pwd, 'stock.picking', 'create', [picking_vals])
        models.execute_kw(db, uid, pwd, 'stock.picking', 'button_validate', [[picking_id]])
        pick_name = models.execute_kw(db, uid, pwd, 'stock.picking', 'read', [picking_id], {'fields': ['name']})[0]['name']
        return f"Stock transferred: {pick_name}"
    except Exception as e:
        return f"Error transferring stock: {str(e)}"

def odoo_adjust_inventory(models, uid, db, pwd, product_id, location_id, new_quantity, reason="Manual"):
    """Adjust inventory quantity"""
    try:
        quants = models.execute_kw(db, uid, pwd, 'stock.quant', 'search_read',
            [[['product_id', '=', int(product_id)], ['location_id', '=', int(location_id)]]], 
            {'fields': ['id'], 'limit': 1})
        
        if quants:
            models.execute_kw(db, uid, pwd, 'stock.quant', 'write', 
                [[quants[0]['id']], {'inventory_quantity': float(new_quantity)}])
            models.execute_kw(db, uid, pwd, 'stock.quant', 'action_apply_inventory', [[quants[0]['id']]])
        else:
            models.execute_kw(db, uid, pwd, 'stock.quant', 'create', [{
                'product_id': int(product_id),
                'location_id': int(location_id),
                'inventory_quantity': float(new_quantity)
            }])
        return f"Inventory adjusted to {new_quantity}. Reason: {reason}"
    except Exception as e:
        return f"Error: {str(e)}"

def odoo_get_warehouse_locations(models, uid, db, pwd):
    """List warehouse storage locations"""
    try:
        locs = models.execute_kw(db, uid, pwd, 'stock.location', 'search_read',
            [[['usage', '=', 'internal']]], 
            {'fields': ['id', 'name', 'complete_name'], 'limit': 20})
        return json.dumps(locs)
    except Exception as e:
        return f"Error: {str(e)}"

def odoo_get_stock_by_location(models, uid, db, pwd, location_id):
    """View inventory in a location"""
    try:
        quants = models.execute_kw(db, uid, pwd, 'stock.quant', 'search_read',
            [[['location_id', '=', int(location_id)], ['quantity', '>', 0]]], 
            {'fields': ['product_id', 'quantity', 'reserved_quantity'], 'limit': 50})
        return json.dumps(quants)
    except Exception as e:
        return f"Error: {str(e)}"

def odoo_create_scrap(models, uid, db, pwd, product_id, quantity, reason="Damaged"):
    """Record product scrap/waste"""
    try:
        scrap_id = models.execute_kw(db, uid, pwd, 'stock.scrap', 'create', [{
            'product_id': int(product_id),
            'scrap_qty': float(quantity),
            'name': reason,
        }])
        models.execute_kw(db, uid, pwd, 'stock.scrap', 'action_validate', [[scrap_id]])
        return f"Scrap recorded: {quantity} units ({reason})"
    except Exception as e:
        return f"Error: {str(e)}"

def odoo_get_product_stock_all_locations(models, uid, db, pwd, product_id):
    """Get stock across all locations"""
    try:
        quants = models.execute_kw(db, uid, pwd, 'stock.quant', 'search_read',
            [[['product_id', '=', int(product_id)], ['quantity', '>', 0]]], 
            {'fields': ['location_id', 'quantity', 'reserved_quantity']})
        return json.dumps(quants)
    except Exception as e:
        return f"Error: {str(e)}"

def odoo_get_incoming_shipments(models, uid, db, pwd):
    """List incoming purchase receipts"""
    try:
        picks = models.execute_kw(db, uid, pwd, 'stock.picking', 'search_read',
            [[['picking_type_code', '=', 'incoming'], ['state', 'not in', ['done', 'cancel']]]], 
            {'fields': ['name', 'origin', 'scheduled_date', 'state'], 'limit': 10})
        return json.dumps(picks)
    except Exception as e:
        return f"Error: {str(e)}"

def odoo_cancel_order(models, uid, db, pwd, order_id):
    try:
        models.execute_kw(db, uid, pwd, 'sale.order', 'action_cancel', [[int(order_id)]])
        return f"Order {order_id} has been cancelled."
    except Exception as e:
        return f"Error cancelling order: {str(e)}"

def odoo_get_invoice_status(models, uid, db, pwd, invoice_id):
    try:
        inv = models.execute_kw(db, uid, pwd, 'account.move', 'read', [int(invoice_id)], {'fields': ['name', 'payment_state', 'amount_residual', 'state']})
        if not inv: return "Invoice not found."
        return json.dumps(inv[0])
    except Exception as e:
        return f"Error fetching invoice status: {str(e)}"

def odoo_list_product_categories(models, uid, db, pwd):
    try:
        cats = models.execute_kw(db, uid, pwd, 'product.category', 'search_read', [[['parent_id', '!=', False]]], {'fields': ['display_name'], 'limit': 10})
        return json.dumps(cats)
    except Exception as e:
        return f"Error fetching categories: {str(e)}"

def odoo_update_quotation_line(models, uid, db, pwd, order_id, product_id, quantity):
    try:
        # Check if order exists and is in draft/sent
        order = models.execute_kw(db, uid, pwd, 'sale.order', 'read', [int(order_id)], {'fields': ['state', 'order_line']})
        if not order or order[0]['state'] not in ['draft', 'sent']:
            return "Order not found or not modifiable (must be draft/sent)."
        
        # Check if line with product exists
        # This is a simplification; usually we'd search inside the lines.
        # For simplicity in this agent, we just add a new line or update if we find exact match? 
        # Writing to (1, id, vals) updates, (0, 0, vals) adds.
        # Let's just append for now or intelligent search?
        # Let's try to add/update via 'order_line' command.
        
        # Search lines
        lines = models.execute_kw(db, uid, pwd, 'sale.order.line', 'search_read', 
            [[['order_id', '=', int(order_id)], ['product_id', '=', int(product_id)]]], 
            {'fields': ['id']})
            
        if lines:
            # Update existing
            line_id = lines[0]['id']
            vals = {'product_uom_qty': float(quantity)}
            models.execute_kw(db, uid, pwd, 'sale.order', 'write', [[int(order_id)], {'order_line': [(1, line_id, vals)]}])
            return f"Updated product {product_id} quantity to {quantity} in Order {order_id}."
        else:
            # Add new
            vals = {'product_id': int(product_id), 'product_uom_qty': float(quantity)}
            models.execute_kw(db, uid, pwd, 'sale.order', 'write', [[int(order_id)], {'order_line': [(0, 0, vals)]}])
            return f"Added product {product_id} with quantity {quantity} to Order {order_id}."
            
    except Exception as e:
        return f"Error updating order: {str(e)}"

def get_openai_response(prompt, history=[], api_key=None, system_context="Be a helpful sales assistant.", models=None, uid=None, chat_id=None, lead_id=None):
    if not api_key:
        return "OpenAI API Key not configured."
    
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "search_products",
                "description": "Search for products in Odoo by name.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_product_details",
                "description": "Get price, stock, and description of a product.",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "send_product_image",
                "description": "Send a product image to the customer Telegram.",
                "parameters": {
                    "type": "object",
                    "properties": {"product_id": {"type": "integer"}},
                    "required": ["product_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_quotation",
                "description": "Create a Quotation (Sale Order) in Odoo and send the PDF to the customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "quantity": {"type": "number", "default": 1}
                    },
                    "required": ["product_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "confirm_sale_order",
                "description": "Confirm a Sale Order to lock it (make it a Sales Order). Required before invoicing.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sale_order_id": {"type": "integer"}
                    },
                    "required": ["sale_order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_invoice",
                "description": "Create an Invoice from a Sale Order. Accepts order name (e.g., 'SO00088') or ID. Auto-confirms if needed and sends PDF.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_ref": {"type": "string", "description": "Order name like 'SO00088' or numeric ID"}
                    },
                    "required": ["order_ref"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_order_by_name",
                "description": "Look up a Sale Order by its name (e.g., 'SO00088'). Returns ID, state, amount.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_name": {"type": "string"}
                    },
                    "required": ["order_name"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_my_orders",
                "description": "List the last 5 orders for the current customer to check status or amounts.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_quotation_line",
                "description": "Update the quantity of a product in a draft quotation/order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer"},
                        "product_id": {"type": "integer"},
                        "quantity": {"type": "number"}
                    },
                    "required": ["order_id", "product_id", "quantity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_order",
                "description": "Cancel a specific sale order or quotation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "order_id": {"type": "integer"}
                    },
                    "required": ["order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_invoice_status",
                "description": "Check the payment status (Paid/Open) of an invoice.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "invoice_id": {"type": "integer"}
                    },
                    "required": ["invoice_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_product_categories",
                "description": "List available product categories to help the user browse.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "validate_delivery",
                "description": "Validate the delivery (ship goods) for a confirmed sale order.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sale_order_id": {"type": "integer"}
                    },
                    "required": ["sale_order_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "register_payment",
                "description": "Register payment for an invoice. Mark as Paid.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "invoice_ref": {"type": "string", "description": "Invoice name (e.g., 'INV/2026/00001') or ID"},
                        "amount": {"type": "number", "description": "Payment amount. Defaults to full balance if omitted."}
                    },
                    "required": ["invoice_ref"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_financial_summary",
                "description": "Get a summary of unpaid invoices and total receivables.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_suppliers",
                "description": "Search for suppliers/vendors by name.",
                "parameters": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_purchase_order",
                "description": "Draft a Purchase Order for a supplier.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "supplier_id": {"type": "integer"},
                        "products": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "product_id": {"type": "integer"},
                                    "quantity": {"type": "number"}
                                },
                                "required": ["product_id", "quantity"]
                            }
                        }
                    },
                    "required": ["supplier_id", "products"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_stock_forecast",
                "description": "Get detailed stock info (On Hand, Incoming, Outgoing) for a product.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"}
                    },
                    "required": ["product_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_my_leads",
                "description": "Get valid CRM Leads/Opportunities for the current user.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "update_lead_phone",
                "description": "Update the phone/mobile number for the lead and customer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "phone": {"type": "string"}
                    },
                    "required": ["phone"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_lead_related_orders",
                "description": "Find Sale Orders linked to the current Lead/Opportunity context.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "transfer_stock",
                "description": "Transfer stock between warehouse locations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "from_location_id": {"type": "integer"},
                        "to_location_id": {"type": "integer"},
                        "quantity": {"type": "number"}
                    },
                    "required": ["product_id", "from_location_id", "to_location_id", "quantity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "adjust_inventory",
                "description": "Adjust inventory quantity at a location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "location_id": {"type": "integer"},
                        "new_quantity": {"type": "number"},
                        "reason": {"type": "string", "default": "Manual"}
                    },
                    "required": ["product_id", "location_id", "new_quantity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_warehouse_locations",
                "description": "List all warehouse storage locations",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_stock_by_location",
                "description": "View inventory in a specific location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_id": {"type": "integer"}
                    },
                    "required": ["location_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_scrap",
                "description": "Record damaged/waste products",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"},
                        "quantity": {"type": "number"},
                        "reason": {"type": "string", "default": "Damaged"}
                    },
                    "required": ["product_id", "quantity"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_product_stock_all_locations",
                "description": "Get stock levels across all locations for a product",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "integer"}
                    },
                    "required": ["product_id"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_incoming_shipments",
                "description": "List incoming purchase receipts/deliveries",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        }
    ]

    # Prepend Human-Simulation Instructions to System Context
    human_instructions = (
        "You are an intelligent Odoo Virtual Employee with full business capabilities."
        "You have access to Sales, Ops, Finance, CRM, and INVENTORY/WAREHOUSE management."
        "For invoices: I auto-confirm orders if needed."
        "For warehouse: You can transfer stock, adjust inventory, view locations, record scrap."
        "When users say 'ship it', use `validate_delivery`."
        "When users say 'paid', use `register_payment`."
        "When they give phone numbers, use `update_lead_phone`."
        "Be efficient, confident, and proactive like a real employee."
    )
    full_system = f"{human_instructions}\n\n{system_context}"

    messages = [{"role": "system", "content": full_system}]
    for h in history:
        messages.append({"role": "user" if h['type'] == 'incoming' else "assistant", "content": h['text']})
    messages.append({"role": "user", "content": prompt})
    
    for _ in range(5):  # Max 5 turns of tool calling
        payload = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto"
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=25)
        res_json = response.json()
        
        if 'error' in res_json:
            return f"AI Error: {res_json['error']['message']}"
            
        message = res_json['choices'][0]['message']
        messages.append(message)
        
        if not message.get('tool_calls'):
            return message['content']
            
        for tool_call in message['tool_calls']:
            func_name = tool_call['function']['name']
            args = json.loads(tool_call['function']['arguments'])
            print(f"Executing tool: {func_name}({args})", flush=True)
            
            if func_name == "search_products":
                result = odoo_search_products(models, uid, DB, PASS, args.get('query'))
            elif func_name == "get_product_details":
                result = odoo_get_product_details(models, uid, DB, PASS, args.get('product_id'))
            elif func_name == "send_product_image":
                result = telegram_send_image(models, uid, DB, PASS, args.get('product_id'), chat_id, TELEGRAM_TOKEN)
            elif func_name == "create_quotation":
                result = odoo_create_quotation(models, uid, DB, PASS, lead_id, args.get('product_id'), args.get('quantity', 1), chat_id, TELEGRAM_TOKEN)
            elif func_name == "confirm_sale_order":
                result = odoo_confirm_order(models, uid, DB, PASS, args.get('sale_order_id'))
            elif func_name == "create_invoice":
                result = odoo_create_invoice(models, uid, DB, PASS, args.get('order_ref'), chat_id, TELEGRAM_TOKEN)
            elif func_name == "get_order_by_name":
                result = odoo_get_order_by_name(models, uid, DB, PASS, args.get('order_name'))
            elif func_name == "get_my_orders":
                result = odoo_get_my_orders(models, uid, DB, PASS, chat_id)
            elif func_name == "update_quotation_line":
                result = odoo_update_quotation_line(models, uid, DB, PASS, args.get('order_id'), args.get('product_id'), args.get('quantity'))
            elif func_name == "cancel_order":
                result = odoo_cancel_order(models, uid, DB, PASS, args.get('order_id'))
            elif func_name == "get_invoice_status":
                result = odoo_get_invoice_status(models, uid, DB, PASS, args.get('invoice_id'))
            elif func_name == "list_product_categories":
                result = odoo_list_product_categories(models, uid, DB, PASS)
            elif func_name == "validate_delivery":
                result = odoo_validate_delivery(models, uid, DB, PASS, args.get('sale_order_id'))
            elif func_name == "register_payment":
                result = odoo_register_payment(models, uid, DB, PASS, args.get('invoice_ref'), args.get('amount'))
            elif func_name == "get_financial_summary":
                result = models.execute_kw(DB, uid, PASS, 'account.move', 'action_ai_get_financial_summary', [])
            elif func_name == "search_suppliers":
                result = models.execute_kw(DB, uid, PASS, 'res.partner', 'action_ai_search_suppliers', [], {'query': args.get('query')})
            elif func_name == "create_purchase_order":
                result = models.execute_kw(DB, uid, PASS, 'purchase.order', 'action_ai_create_purchase_order', [], {
                    'supplier_id': args.get('supplier_id'),
                    'products': args.get('products')
                })
            elif func_name == "get_stock_forecast":
                result = odoo_get_stock_forecast(models, uid, DB, PASS, args.get('product_id'))
            elif func_name == "get_my_leads":
                result = odoo_get_my_leads(models, uid, DB, PASS, chat_id)
            elif func_name == "update_lead_phone":
                result = odoo_update_lead_phone(models, uid, DB, PASS, lead_id, args.get('phone'))
            elif func_name == "get_lead_related_orders":
                result = odoo_get_lead_related_orders(models, uid, DB, PASS, lead_id)
            elif func_name == "transfer_stock":
                result = odoo_transfer_stock(models, uid, DB, PASS, args.get('product_id'), args.get('from_location_id'), args.get('to_location_id'), args.get('quantity'))
            elif func_name == "adjust_inventory":
                result = odoo_adjust_inventory(models, uid, DB, PASS, args.get('product_id'), args.get('location_id'), args.get('new_quantity'), args.get('reason', 'Manual'))
            elif func_name == "get_warehouse_locations":
                result = odoo_get_warehouse_locations(models, uid, DB, PASS)
            elif func_name == "get_stock_by_location":
                result = odoo_get_stock_by_location(models, uid, DB, PASS, args.get('location_id'))
            elif func_name == "create_scrap":
                result = odoo_create_scrap(models, uid, DB, PASS, args.get('product_id'), args.get('quantity'), args.get('reason', 'Damaged'))
            elif func_name == "get_product_stock_all_locations":
                result = odoo_get_product_stock_all_locations(models, uid, DB, PASS, args.get('product_id'))
            elif func_name == "get_incoming_shipments":
                result = odoo_get_incoming_shipments(models, uid, DB, PASS)
            else:
                result = "Unknown tool."
                
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call['id'],
                "name": func_name,
                "content": result
            })
            
    return "Max tool execution depth reached."

def run_bot():
    print("Starting Telegram Bot Poller...", flush=True)
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, USER, PASS, {})
        if not uid:
            print("Odoo Authentication Failed!", flush=True)
            return
        print(f"Odoo Authenticated. UID: {uid}", flush=True)
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    except Exception as e:
        print(f"Odoo Connection Error: {e}", flush=True)
        return

    last_update_id = 0
    print("Entering polling loop...", flush=True)
    
    while True:
        try:
            tg_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(tg_url, timeout=40)
            result_json = response.json()
            if not result_json.get('ok'):
                print(f"Telegram API Error: {result_json}", flush=True)
                time.sleep(5)
                continue
                
            updates = result_json.get('result', [])

            for update in updates:
                last_update_id = update['update_id']
                if 'message' not in update: continue
                
                msg = update['message']
                chat_id = str(msg['chat']['id'])
                user_name = msg['from'].get('first_name', 'Unknown')
                # 1. Handle Voice or Text
                voice = msg.get('voice')
                if voice:
                    # Need OpenAI Key for transcription
                    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    requests.post(send_url, json={'chat_id': chat_id, 'text': "🎤 Processing your voice note..."})
                    
                    temp_key = models.execute_kw(DB, uid, PASS, 'ir.config_parameter', 'get_param', ['lead_telegram_agent.openai_key'])
                    text = transcribe_voice(voice['file_id'], TELEGRAM_TOKEN, temp_key)
                    print(f"Transcribed voice from {user_name}: {text}", flush=True)
                    if not text:
                        requests.post(send_url, json={'chat_id': chat_id, 'text': "Sorry, I couldn't understand that voice message. Could you try again or type it out?"})
                        continue
                else:
                    text = msg.get('text', '')

                if not text: continue

                # 2. Find or Create Lead
                lead_ids = models.execute_kw(DB, uid, PASS, 'crm.lead', 'search', [[['telegram_chat_id', '=', chat_id]]])
                
                if lead_ids:
                    lead_id = lead_ids[0]
                else:
                    # Create new lead
                    lead_vals = {
                        'name': f"Telegram Lead: {user_name}",
                        'telegram_chat_id': chat_id,
                        'description': f"Created from Telegram bot. User: {user_name}",
                        'type': 'lead',
                    }
                    lead_id = models.execute_kw(DB, uid, PASS, 'crm.lead', 'create', [lead_vals])
                    print(f"Created new Lead ID: {lead_id}", flush=True)

                # 3. Get Lead Data and History for AI Context
                lead = models.execute_kw(DB, uid, PASS, 'crm.lead', 'read', [lead_id], {'fields': ['is_ai_agent_enabled', 'ai_agent_context', 'name']})[0]
                
                # 2. Get AI Settings from Odoo
                config = models.execute_kw(DB, uid, PASS, 'ir.config_parameter', 'get_param', ['lead_telegram_agent.openai_key'])
                openai_key = config or OPENAI_KEY
                
                global_system_prompt = models.execute_kw(DB, uid, PASS, 'ir.config_parameter', 'get_param', ['lead_telegram_agent.system_prompt']) or "You are a helpful Odoo Assistant."
                ai_role = models.execute_kw(DB, uid, PASS, 'ir.config_parameter', 'get_param', ['lead_telegram_agent.ai_role']) or "general"
                
                # Role-based prompt adjustment
                role_prompts = {
                    'sales': " You are a Sales Agent. Focus on leads and quotations.",
                    'accounting': " You are an Accountant/Bookkeeper. Focus on invoices, payments, and financial status.",
                    'inventory': " You are a Warehouse Manager. Focus on stock, locations, and shipments.",
                    'general': " You are a Complete Virtual Employee. You handle Sales, Accounting, and Ops."
                }
                global_system_prompt += role_prompts.get(ai_role, "")
                # Fetch recent history from mail.message
                history = []
                messages_data = models.execute_kw(DB, uid, PASS, 'mail.message', 'search_read', 
                                                 [[['res_id', '=', lead_id], ['model', '=', 'crm.lead'], ['message_type', '=', 'comment']]], 
                                                 {'fields': ['body'], 'limit': 30, 'order': 'date desc'})
                import re
                print(f"DEBUG: Found {len(messages_data)} previous messages in Chatter.", flush=True)
                for m in reversed(messages_data):
                    body = m.get('body', '')
                    # Robust Parsing: Look for the markers regardless of exact tag format
                    # Odoo often wraps in <p> or adds whitespace
                    user_match = re.search(r"Telegram \(.*?\):</b>(.*?)(?=<br/>|<b>AI Agent:</b>|$)", body, re.DOTALL | re.IGNORECASE)
                    ai_match = re.search(r"AI Agent:</b>(.*?)$", body, re.DOTALL | re.IGNORECASE)
                    
                    if user_match and ai_match:
                        user_text = re.sub('<[^<]+?>', '', user_match.group(1)).strip()
                        ai_text = re.sub('<[^<]+?>', '', ai_match.group(1)).strip()
                        history.append({'type': 'incoming', 'text': user_text})
                        history.append({'type': 'outgoing', 'text': ai_text})
                    else:
                        # Fallback: if we can't parse markers, just treat as system/info but don't add to AI history to avoid junk
                        pass

                print(f"DEBUG: Constructed History: {history}", flush=True)

                if lead.get('is_ai_agent_enabled'):
                    lead_context = lead.get('ai_agent_context') or ""
                    full_system_context = f"{global_system_prompt}\n\nLead Specific Context: {lead_context}" if lead_context else global_system_prompt
                    
                    print(f"Generating OpenAI response (with {len(history)} items history)...", flush=True)
                    ai_reply = get_openai_response(text, history=history, api_key=openai_key, 
                                                  system_context=full_system_context,
                                                  models=models, uid=uid, chat_id=chat_id, lead_id=lead_id)
                    
                    # 4. Send Reply to Telegram
                    send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
                    tg_res = requests.post(send_url, json={'chat_id': chat_id, 'text': ai_reply})
                    if not tg_res.ok:
                        print(f"FAILED TO SEND TO TELEGRAM: {tg_res.text}", flush=True)
                    else:
                        print(f"Sent response to {user_name} ({chat_id})", flush=True)
                    
                    # 5. Log to Odoo Chatter
                    # Use a clean format that we can parse back if needed
                    log_msg = f"<b>Telegram ({user_name}):</b> {text}<br/><b>AI Agent:</b> {ai_reply}"
                    models.execute_kw(DB, uid, PASS, 'crm.lead', 'message_post', [lead_id], {'body': log_msg})
                else:
                    # Just log the message if AI is disabled
                    log_msg = f"<b>Telegram ({user_name}):</b> {text} (AI Agent Disabled)"
                    models.execute_kw(DB, uid, PASS, 'crm.lead', 'message_post', [lead_id], {'body': log_msg})

        except Exception as e:
            print(f"Poller Error: {e}", flush=True)
            time.sleep(5)

if __name__ == "__main__":
    run_bot()
