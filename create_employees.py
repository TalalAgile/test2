import xmlrpc.client
import time

def create_odoo_employees():
    url = "https://talalagile-test2.odoo.com"
    db = "talalagile-test2-main-27890898"
    username = "admin"
    password = "123"

    print(f"Connecting to {url} for employee creation...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("Authentication failed!")
            return

        print(f"Authenticated successfully. UID: {uid}")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        # Create 100 employees
        for i in range(1, 101):
            employee_name = f"Auto-Employee {i}"
            employee_vals = {
                'name': employee_name,
                'work_email': f"auto.employee.{i}@example.com",
            }
            
            try:
                employee_id = models.execute_kw(db, uid, password, 'hr.employee', 'create', [employee_vals])
                print(f"[{i}/100] Created employee: {employee_name} (ID: {employee_id})")
            except Exception as e:
                print(f"[{i}/100] Failed to create {employee_name}: {e}")
            
        print("\nSuccessfully processed 100 employee creation requests.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_odoo_employees()
