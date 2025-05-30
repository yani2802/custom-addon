from odoo import http
from odoo.http import request
import logging
import json
from datetime import datetime, timedelta
import secrets
import hashlib

_logger = logging.getLogger(__name__)

class HardwareAuthController(http.Controller):
    
    @http.route('/hardware/auth/login', type='json', auth='none', methods=['POST'], csrf=False)
    def authenticate_agent(self, **kwargs):
        """Authenticate hardware agent"""
        try:
            agent_name = kwargs.get('agent_name')
            agent_key = kwargs.get('agent_key')
            agent_version = kwargs.get('version', '1.0.0')
            
            if not agent_name or not agent_key:
                return {
                    'success': False, 
                    'error': 'Missing agent credentials',
                    'code': 'MISSING_CREDENTIALS'
                }
            
            # Find or create hardware agent
            agent = self._find_or_create_agent(agent_name, agent_key, agent_version)
            
            if not agent:
                return {
                    'success': False, 
                    'error': 'Invalid agent credentials',
                    'code': 'INVALID_CREDENTIALS'
                }
            
            # Generate session token
            token = self._generate_session_token(agent)
            
            # Update agent status
            agent.sudo().write({
                'status': 'online',
                'last_heartbeat': datetime.now(),
                'ip_address': request.httprequest.remote_addr,
                'version': agent_version,
            })
            
            return {
                'success': True,
                'token': token,
                'agent_id': agent.id,
                'agent_name': agent.name,
                'permissions': self._get_agent_permissions(agent),
                'config': self._get_agent_config(agent)
            }
            
        except Exception as e:
            _logger.error("Agent authentication error: %s", str(e))
            return {
                'success': False, 
                'error': 'Internal authentication error',
                'code': 'INTERNAL_ERROR'
            }
    
    @http.route('/hardware/auth/verify', type='json', auth='none', methods=['POST'], csrf=False)
    def verify_token(self, **kwargs):
        """Verify authentication token"""
        try:
            token = kwargs.get('token')
            agent_id = kwargs.get('agent_id')
            
            if not token or not agent_id:
                return {'valid': False, 'error': 'Missing token or agent_id'}
            
            agent = request.env['hardware.agent'].sudo().browse(int(agent_id))
            if not agent.exists():
                return {'valid': False, 'error': 'Agent not found'}
            
            if self._verify_session_token(token, agent):
                # Update last heartbeat
                agent.write({'last_heartbeat': datetime.now()})
                return {
                    'valid': True,
                    'agent_name': agent.name,
                    'permissions': self._get_agent_permissions(agent)
                }
            else:
                return {'valid': False, 'error': 'Invalid or expired token'}
                
        except Exception as e:
            _logger.error("Token verification error: %s", str(e))
            return {'valid': False, 'error': 'Verification failed'}
    
    @http.route('/hardware/auth/heartbeat', type='json', auth='none', methods=['POST'], csrf=False)
    def heartbeat(self, **kwargs):
        """Agent heartbeat endpoint"""
        try:
            token = kwargs.get('token')
            agent_id = kwargs.get('agent_id')
            status_data = kwargs.get('status', {})
            
            if not self._verify_request(token, agent_id):
                return {'success': False, 'error': 'Authentication failed'}
            
            agent = request.env['hardware.agent'].sudo().browse(int(agent_id))
            
            # Update agent status
            update_vals = {
                'last_heartbeat': datetime.now(),
                'status': 'online',
            }
            
            if status_data:
                update_vals['status_data'] = json.dumps(status_data)
            
            agent.write(update_vals)
            
            return {
                'success': True,
                'server_time': datetime.now().isoformat(),
                'config_updated': False  # Could check for config changes
            }
            
        except Exception as e:
            _logger.error("Heartbeat error: %s", str(e))
            return {'success': False, 'error': 'Heartbeat failed'}
    
    @http.route('/hardware/auth/logout', type='json', auth='none', methods=['POST'], csrf=False)
    def logout_agent(self, **kwargs):
        """Logout hardware agent"""
        try:
            token = kwargs.get('token')
            agent_id = kwargs.get('agent_id')
            
            if not self._verify_request(token, agent_id):
                return {'success': False, 'error': 'Authentication failed'}
            
            agent = request.env['hardware.agent'].sudo().browse(int(agent_id))
            agent.write({
                'status': 'offline',
                'session_token': False,
            })
            
            return {'success': True, 'message': 'Logged out successfully'}
            
        except Exception as e:
            _logger.error("Logout error: %s", str(e))
            return {'success': False, 'error': 'Logout failed'}
    
    def _find_or_create_agent(self, agent_name, agent_key, version):
        """Find existing agent or create new one"""
        try:
            # First try to find existing agent
            agent = request.env['hardware.agent'].sudo().search([
                ('name', '=', agent_name)
            ], limit=1)
            
            if agent:
                # Verify agent key
                if self._verify_agent_key(agent, agent_key):
                    return agent
                else:
                    _logger.warning(f"Invalid key for existing agent: {agent_name}")
                    return None
            else:
                # Create new agent
                agent_id = self._generate_agent_id(agent_name)
                agent = request.env['hardware.agent'].sudo().create({
                    'name': agent_name,
                    'agent_id': agent_id,
                    'agent_key': self._hash_agent_key(agent_key),
                    'status': 'offline',
                    'version': version,
                    'created_date': datetime.now(),
                })
                _logger.info(f"Created new hardware agent: {agent_name}")
                return agent
                
        except Exception as e:
            _logger.error(f"Error finding/creating agent {agent_name}: {e}")
            return None
    
    def _verify_agent_key(self, agent, provided_key):
        """Verify agent key"""
        try:
            stored_hash = agent.agent_key
            provided_hash = self._hash_agent_key(provided_key)
            return stored_hash == provided_hash
        except Exception:
            return False
    
    def _hash_agent_key(self, key):
        """Hash agent key for storage"""
        return hashlib.sha256(key.encode()).hexdigest()
    
    def _generate_agent_id(self, agent_name):
        """Generate unique agent ID"""
        timestamp = str(int(datetime.now().timestamp()))
        name_hash = hashlib.md5(agent_name.encode()).hexdigest()[:8]
        return f"agent_{name_hash}_{timestamp}"
    
    def _generate_session_token(self, agent):
        """Generate session token for agent"""
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Store token hash in agent record
        agent.sudo().write({
            'session_token': token_hash,
            'token_expires': datetime.now() + timedelta(hours=24),
        })
        
        return token
    
    def _verify_session_token(self, token, agent):
        """Verify session token"""
        try:
            if not agent.session_token or not agent.token_expires:
                return False
            
            # Check if token expired
            if datetime.now() > agent.token_expires:
                return False
            
            # Verify token hash
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            return token_hash == agent.session_token
            
        except Exception:
            return False
    
    def _verify_request(self, token, agent_id):
        """Verify request authentication"""
        try:
            if not token or not agent_id:
                return False
            
            agent = request.env['hardware.agent'].sudo().browse(int(agent_id))
            if not agent.exists():
                return False
            
            return self._verify_session_token(token, agent)
            
        except Exception:
            return False
    
    def _get_agent_permissions(self, agent):
        """Get agent permissions"""
        # Default permissions for hardware agents
        return [
            'device_discovery',
            'device_connect',
            'device_scan',
            'status_report',
            'config_read'
        ]
    
    def _get_agent_config(self, agent):
        """Get agent configuration"""
        return {
            'scan_interval': 30,
            'heartbeat_interval': 60,
            'auto_connect': True,
            'supported_devices': [
                'barcode_scanner',
                'nfc_reader', 
                'qr_scanner',
                'printer'
            ],
            'network_scan_range': '192.168.1.0/24',
            'max_devices': 10
        }