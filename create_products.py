import xmlrpc.client
import time

def create_odoo_products():
    url = "https://talalagile-test2.odoo.com"
    db = "talalagile-test2-main-27890898"
    username = "admin"
    password = "123"

    print(f"Connecting to {url}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("Authentication failed!")
            return

        print(f"Authenticated successfully. UID: {uid}")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # Create 100 products
        for i in range(1, 101):
            product_name = f"Auto-Product {i}"
            product_vals = {
                'name': product_name,
                'type': 'consu', # Consumable
                'sale_ok': True,
                'purchase_ok': True,
            }
            
            product_id = models.execute_kw(db, uid, password, 'product.template', 'create', [product_vals])
            print(f"[{i}/100] Created product: {product_name} (ID: {product_id})")
            
            # Optional: Small sleep to avoid throttling if any
            # time.sleep(0.1)

        print("\nSuccessfully created 100 products.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_odoo_products()
