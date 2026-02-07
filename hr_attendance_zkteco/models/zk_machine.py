from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

try:
    from zk import ZK, const
except ImportError:
    _logger.error("Could not import ZK library. Please install it with 'pip install pyzk'")

class ZKMachine(models.Model):
    _name = 'zk.machine'
    _description = 'ZKTeco Attendance Machine'

    name = fields.Char(string='Machine Name', required=True)
    ip_address = fields.Char(string='IP Address', required=True)
    port = fields.Integer(string='Port', default=4370, required=True)
    timeout = fields.Integer(string='Timeout', default=30)
    ommit_ping = fields.Boolean(string='Skip Ping', default=False, help="Skip pinging the device before connecting. Useful if the network blocks ICMP (Ping).")
    connection_method = fields.Selection([
        ('udp', 'UDP (Default)'),
        ('tcp', 'TCP (Force)'),
    ], string='Connection Method', default='udp', required=True)
    is_active = fields.Boolean(string='Active', default=True)

    last_sync_date = fields.Datetime(string='Last Sync Date', readonly=True)

    def test_connection(self):
        self.ensure_one()
        if 'ZK' not in globals():
            raise UserError(_("The 'pyzk' library is not installed on the server. Please run 'pip install pyzk' on the server and restart Odoo."))
        
        force_udp = True if self.connection_method == 'udp' else False
        zk = ZK(self.ip_address, port=self.port, timeout=self.timeout, password=0, force_udp=force_udp, ommit_ping=self.ommit_ping)

        conn = None
        try:
            conn = zk.connect()
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Connection Successful'),
                    'message': _('Successfully connected to machine: %s') % (self.name),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_("Connection failed: %s") % str(e))
        finally:
            if conn:
                conn.disconnect()

    def sync_attendance(self):
        if 'ZK' not in globals():
            raise UserError(_("The 'pyzk' library is not installed on the server. Please run 'pip install pyzk' on the server and restart Odoo."))
            
        for machine in self:
            force_udp = True if machine.connection_method == 'udp' else False
            zk = ZK(machine.ip_address, port=machine.port, timeout=machine.timeout, password=0, force_udp=force_udp, ommit_ping=machine.ommit_ping)


            conn = None
            try:
                conn = zk.connect()
                conn.disable_device()
                attendance = conn.get_attendance()
                
                if attendance:
                    for log in attendance:
                        # Find employee by ZK Machine ID
                        employee = self.env['hr.employee'].search([('zk_machine_id', '=', str(log.user_id))], limit=1)
                        if not employee:
                            _logger.info("Employee not found for machine ID: %s", log.user_id)
                            continue

                        # Check if attendance already exists
                        existing = self.env['hr.attendance'].search([
                            ('employee_id', '=', employee.id),
                            ('check_in', '=', log.timestamp)
                        ], limit=1)

                        if not existing:
                            self.env['hr.attendance'].create({
                                'employee_id': employee.id,
                                'check_in': log.timestamp,
                            })
                    
                    machine.last_sync_date = fields.Datetime.now()
                
                conn.enable_device()
            except Exception as e:
                _logger.error("Sync failed for machine %s: %s", machine.name, str(e))
                raise UserError(_("Sync failed: %s") % str(e))
            finally:
                if conn:
                    conn.disconnect()

    @api.model
    def cron_sync_attendance(self):
        machines = self.search([('is_active', '=', True)])
        machines.sync_attendance()
