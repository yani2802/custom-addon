import socket
import struct

def test_printer_communication(ip, port=9100):
    """Test actual printer communication"""
    try:
        # Connect to printer
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        
        # Send test print job (ESC/P or PCL)
        test_job = b'\x1b\x40'  # ESC @ (Initialize printer)
        test_job += b'Hardware Test Print\n'
        test_job += b'Timestamp: ' + str(datetime.now()).encode() + b'\n'
        test_job += b'\x0c'  # Form feed
        
        sock.send(test_job)
        sock.close()
        
        return True
    except Exception as e:
        return False

def get_printer_status(ip, port=9100):
    """Get actual printer status"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((ip, port))
        
        # Send status request
        status_request = b'\x1b\x40\x1b\x28\x41\x01\x00\x01'
        sock.send(status_request)
        
        response = sock.recv(1024)
        sock.close()
        
        return parse_printer_status(response)
    except Exception:
        return {'status': 'offline'} 