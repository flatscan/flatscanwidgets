#!/usr/bin/python
# coding: utf-8

"""
Main service monitor.
Coordinates background tasks and responds to events.
"""

import xbmc
import xbmcgui
from resources.lib.addon import ADDON
from resources.lib.logger import log
from resources.lib.service.blur_service import BlurService
from resources.lib.service.fanart_service import FanartService


class ServiceMonitor(xbmc.Monitor):
    """
    Main service monitor class.
    Handles Kodi events and coordinates background services.
    """
    
    def __init__(self):
        super().__init__()
        self._shutdown = False
        self._restart = False
        
        # Initialize sub-services
        self.blur_service = BlurService()
        self.fanart_service = FanartService()
        
        log('Service: Initialized')
        
    def start(self):
        """Start the service loop."""
        log('Service: Started')
        
        # Check if service is enabled in settings
        if not ADDON.getSettingBool('service_enabled'):
            log('Service: Disabled in settings')
            self._keep_alive()
            return
            
        # Start sub-services
        self.blur_service.start()
        self.fanart_service.start()
        
        # Main service loop
        self._run_loop()
        
    def _run_loop(self):
        """Main service loop."""
        while not self._shutdown and not self.abortRequested():
            # Check for restart request
            if self._restart:
                self._handle_restart()
                continue
                
            # Wait for abort (checks every 1 second)
            if self.waitForAbort(1):
                break
                
        # Cleanup
        self._cleanup()
        
    def _keep_alive(self):
        """Minimal loop when service is disabled."""
        log('Service: Running in keep-alive mode')
        while not self.abortRequested():
            if self.waitForAbort(5):
                break
                
    def _handle_restart(self):
        """Handle service restart."""
        log('Service: Restarting...')
        self._restart = False
        self._cleanup()
        xbmc.sleep(500)  # Brief pause before restart
        self.__init__()
        self.start()
        
    def _cleanup(self):
        """Cleanup on shutdown."""
        log('Service: Cleaning up...')
        self.blur_service.stop()
        self.fanart_service.stop()
        self._shutdown = True
        
    # --- Kodi Event Handlers ---
    
    def onNotification(self, sender, method, data):
        """
        Handle Kodi notifications.
        
        Args:
            sender: Addon that sent notification
            method: Notification method
            data: Notification data
        """
        # Handle library updates
        if method in ['VideoLibrary.OnUpdate', 'VideoLibrary.OnScanFinished']:
            log(f'Service: Library update detected ({method})')
            # Trigger widget refresh via window property
            xbmcgui.Window(10000).setProperty('FlatscanWidgetUpdate', '1')
            xbmc.sleep(100)
            xbmcgui.Window(10000).clearProperty('FlatscanWidgetUpdate')
            
    def onSettingsChanged(self):
        """Handle settings changes."""
        log('Service: Settings changed')
        self._restart = True
        
    def onScreensaverActivated(self):
        """Handle screensaver activation."""
        log('Service: Screensaver activated')
        self.blur_service.pause()
        self.fanart_service.pause()
        
    def onScreensaverDeactivated(self):
        """Handle screensaver deactivation."""
        log('Service: Screensaver deactivated')
        self.blur_service.resume()
        self.fanart_service.resume()


def main():
    """Service entry point."""
    monitor = ServiceMonitor()
    monitor.start()


if __name__ == '__main__':
    main()