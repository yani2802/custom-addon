import jwt
from cryptography.fernet import Fernet
import hashlib
import hmac

class SecurityManager:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.cipher = Fernet(Fernet.generate_key())
    
    def generate_api_token(self, hub_id, expires_hours=24):
        """Generate secure API token"""
        payload = {
            'hub_id': hub_id,
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token):
        """Verify API token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive device data"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive device data"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()