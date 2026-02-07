import xmlrpc.client
import random

def create_furniture_tech_products():
    url = "https://talalagile-test2.odoo.com"
    db = "talalagile-test2-main-27890898"
    username = "admin"
    password = "123"

    products_data = [
        ("Aura Smart Bed", 2499.00, "IoT-connected bed with sleep tracking and climate control."),
        ("Nexus Sit-Stand Desk", 850.00, "Ergonomic electric desk with posture reminders and USB-C integration."),
        ("Zenith Adaptive Chair", 520.00, "AI-powered lumbar support that adjusts in real-time."),
        ("Lumina Tech-Sofa", 1800.00, "Modular sofa with built-in wireless charging and surround sound."),
        ("Nova Smart Bookshelf", 450.00, "Smart shelving with LED mood lighting and inventory sensors."),
        ("Pinnacle Gaming Station", 3200.00, "Multi-screen adjustable cockpit for professional gaming and dev work."),
        ("Orbit Floating Table", 750.00, "Magnetic levitation side table with minimalist touch controls."),
        ("Stellar Smart Mirror", 600.00, "Bathroom mirror with integrated health stats and weather display."),
        ("Titan Heavy-Duty Tech Workbench", 1200.00, "Motorized workbench with integrated power strips and tool tracking."),
        ("Cosmos Multi-Functional Ottoman", 290.00, "Storage ottoman with built-in Bluetooth speakers and hidden fridge."),
        ("Aether Sound-Proofing Partition", 380.00, "Smart acoustic panel that cancels ambient office noise."),
        ("Vortex Rotating Standing Desk", 980.00, "Fully rotational desk for dynamic workspace setups."),
        ("Eclipse Blackout Nightstand", 320.00, "Nightstand with automatic dimming and sunrise alarm system."),
        ("Pulse Fitness Bench", 890.00, "Workout bench with built-in resistance sensors and tablet mount."),
        ("Glow Intelligent Wardrobe", 1500.00, "Wardrobe with UV disinfection and clothes steaming feature."),
        ("Vista Smart Window Blind", 180.00, "IoT blinds that adjust based on sunlight intensity and time."),
        ("Apex Ergonomic Footrest", 120.00, "Heated footrest with vibration massage and height adjustment."),
        ("Core Home Office Pod", 9500.00, "Soundproof modular pod with integrated AC and 5G router."),
        ("Spark Modular LED Coffee Table", 480.00, "Customizable LED surface with interactive gaming modes."),
        ("Relay Wireless Charging Sideboard", 650.00, "Sideboard with full-surface induction charging."),
        ("Halo Circular Smart Desk", 1100.00, "Minimalist circular desk with hidden cable management."),
        ("Zen Bamboo Tech-Desk", 780.00, "Sustainable bamboo desk with hidden touch controls."),
        ("Atlas Motorized Storage Rack", 1400.00, "Ceiling-mounted storage that lowers via voice command."),
        ("Flow Hydration-Tracking Desk", 900.00, "Desk with integrated water dispenser and hydration reminders."),
        ("Shield Privacy Desk-Screen", 210.00, "Transparent OLED screen that becomes opaque for privacy."),
        ("Beacon Floor Lamp with USB", 250.00, "Smart lamp with multiple charging ports and color temp sync."),
        ("Summit VR-Ready Swivel Chair", 680.00, "High-rotation chair optimized for VR movement."),
        ("Matrix Modular Wall Unit", 2200.00, "Wall system with integrated projector and fold-out desk."),
        ("Cylix Smart Humidifier Cabinet", 340.00, "Storage cabinet with automated climate control for fine wood."),
        ("Tether Cable-Management Hub", 85.00, "Smart power strip with remote monitoring via app."),
        ("Prism Digital Display Frame", 420.00, "Large e-ink frame for dynamic art or system dashboards."),
        ("Origin Ergonomic Keyboard Tray", 150.00, "Adaptive tray with wrist support and haptic feedback."),
        ("Lyric Integrated Media Bench", 1250.00, "TV stand with built-in hi-fi speakers and subwoofers."),
        ("Terra IoT Planter Stand", 195.00, "Connected stand with soil moisture and light level alerts."),
        ("Haven Relax Pod", 4500.00, "Egg-shaped sensory deprivation chair with light therapy."),
        ("Signal Mesh-Network Desk", 1050.00, "Desk that acts as a Wi-Fi 6 mesh node for the office."),
        ("Orbit Rotating TV Wall Mount", 310.00, "Motorized mount that follows user position for optimal viewing."),
        ("Forge 3D-Printing Cabinet", 850.00, "Enclosed cabinet with ventilation for 3D printing equipment."),
        ("Sol Pro Solar-Charging Patio Table", 920.00, "Outdoor table with integrated solar panels and battery bank."),
        ("Aura Mini Tech-Sofa", 950.00, "Compact tech-integrated sofa for small studio apartments."),
        ("Krypton Secure Document Safe", 580.00, "Biometric safe integrated into a sleek side table."),
        ("Neon RGB Interactive Bar Stool", 280.00, "Stool with music-synced RGB lighting and premium upholstery."),
        ("Helios Ultra-Bright Vanity Mirror", 540.00, "Mirror with studio lighting and voice-controlled brightness."),
        ("Vector Pro Drafting Table", 1600.00, "Large-format digital drafting surface for architects."),
        ("Oasis Indoor Garden System", 2100.00, "Fully automated hydroponic cabinet for fresh greens."),
        ("Peak Standing Desk Treadmill", 1350.00, "Ultra-quiet treadmill designed specifically for under-desk use."),
        ("Swift Wireless Peripheral Drawer", 140.00, "Drawer with integrated charging for mice and keyboards."),
        ("Crest Luxury Recliner with AI", 2700.00, "Recliner that analyzes muscle tension to provide custom massage."),
        ("Logic Smart Conference Table", 5600.00, "12-person table with pop-up monitors and 360-degree cameras."),
        ("Vantage Smart Wall Clock", 190.00, "Digital clock that displays calendar sync and task priorities.")
    ]

    print(f"Connecting to Odoo at {url}...")
    try:
        common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
        uid = common.authenticate(db, username, password, {})
        
        if not uid:
            print("Authentication failed!")
            return

        print(f"Authenticated. UID: {uid}")
        models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

        for i, (name, price, desc) in enumerate(products_data, 1):
            product_vals = {
                'name': name,
                'list_price': price,
                'standard_price': price * 0.6,
                'description_sale': desc,
                'type': 'product', # Storable product
                'sale_ok': True,
                'purchase_ok': True,
            }
            
            product_id = models.execute_kw(db, uid, password, 'product.template', 'create', [product_vals])
            print(f"[{i}/50] Created product: {name} (ID: {product_id})")

        print("\nSuccessfully created 50 Furniture Technology products.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    create_furniture_tech_products()
