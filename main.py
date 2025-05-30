"""
Hardware Client Agent - Local Device Detection Service
=====================================================

This application runs as a background service to detect and manage
hardware devices connected via USB, Bluetooth, or WiFi.
"""

import sys
import signal
import threading
import time
from pathlib import Path

from config import Config
from services.device_manager import DeviceManager
from services.background_service import BackgroundService
from utils.logger import setup_logger
from utils.system_tray import SystemTrayApp

logger = setup_logger(__name__)

class HardwareClientAgent:
    def __init__(self):
        self.config = Config()
        self.device_manager = DeviceManager()
        self.background_service = BackgroundService(self.device_manager)
        self.system_tray = None
        self.running = False
        
    def start(self):
        """Start the hardware client agent"""
        logger.info("Starting Hardware Client Agent...")
        
        try:
            # Start device detection
            self.device_manager.start_detection()
            
            # Start background service
            self.background_service.start()
            
            # Start system tray (if GUI available)
            if self.config.ENABLE_SYSTEM_TRAY:
                self.system_tray = SystemTrayApp(self.device_manager)
                tray_thread = threading.Thread(target=self.system_tray.run)
                tray_thread.daemon = True
                tray_thread.start()
            
            self.running = True
            logger.info("Hardware Client Agent started successfully")
            
            # Keep main thread alive
            self.main_loop()
            
        except Exception as e:
            logger.error(f"Failed to start Hardware Client Agent: {e}")
            sys.exit(1)
    
    def stop(self):
        """Stop the hardware client agent"""
        logger.info("Stopping Hardware Client Agent...")
        
        self.running = False
        
        if self.background_service:
            self.background_service.stop()
        
        if self.device_manager:
            self.device_manager.stop_detection()
        
        if self.system_tray:
            self.system_tray.stop()
        
        logger.info("Hardware Client Agent stopped")
    
    def main_loop(self):
        """Main application loop"""
        while self.running:
            try:
                time.sleep(1)
                
                # Periodic health check
                if not self.background_service.is_alive():
                    logger.warning("Background service died, restarting...")
                    self.background_service.restart()
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info(f"Received signal {signum}")
    if hasattr(signal_handler, 'agent'):
        signal_handler.agent.stop()
    sys.exit(0)

def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start agent
    agent = HardwareClientAgent()
    signal_handler.agent = agent
    
    try:
        agent.start()
    except KeyboardInterrupt:
        agent.stop()

if __name__ == "__main__":
    main()