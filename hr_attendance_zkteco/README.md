# ZKTeco Attendance Integration

This module integrates ZKTeco biometric machines with Odoo Attendance.

## Features
- Configure multiple ZK machines.
- Test connection.
- Manually sync attendance logs.
- Automatic synchronization via scheduled action (every hour).
- Matches employees using the `Barcode` (Identity Card ID) field in Odoo.

## Requirements
- Python library `pyzk` (`pip install pyzk`)

## Configuration
1. Install the module.
2. Go to `Attendances > ZK Attendance > ZK Machines`.
3. Create a new machine record with the IP address and Port of your device.
4. Ensure employees in Odoo have their Machine User ID entered in the `Barcode` field.
