#!/usr/bin/python
# coding: utf-8

"""
Blur service - Automatically blurs background images.
"""

import xbmc
import xbmcgui
import threading
from resources.lib.addon import ADDON
from resources.lib.logger import log
from resources.lib.image.blur import ImageBlur


class BlurService:
    """
    Background blur service.
    Monitors for background image changes and applies blur effect.
    """
    
    def __init__(self):
        self._running = False
        self._paused = False
        self._thread = None
        self._last_image = ''
        
        # Get settings
        self.enabled = ADDON.getSettingBool('blur_enabled')
        self.interval = ADDON.getSettingInt('blur_interval') or 500  # ms
        self.radius = ADDON.getSettingInt('blur_radius') or 20
        self.saturation = ADDON.getSetting('blur_saturation') or '1.0'
        
        # Container to monitor (skin string or default)
        self.container = xbmc.getInfoLabel('Skin.String(BlurContainer)') or '100000'
        
        log(f'BlurService: Initialized (enabled={self.enabled})')
        
    def start(self):
        """Start the blur service."""
        if not self.enabled:
            log('BlurService: Disabled')
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._run)
        self._thread.daemon = True
        self._thread.start()
        log('BlurService: Started')
        
    def stop(self):
        """Stop the blur service."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        log('BlurService: Stopped')
        
    def pause(self):
        """Pause the service (e.g., during screensaver)."""
        self._paused = True
        log('BlurService: Paused')
        
    def resume(self):
        """Resume the service."""
        self._paused = False
        log('BlurService: Resumed')
        
    def _run(self):
        """Main blur loop."""
        while self._running:
            if self._paused:
                xbmc.sleep(100)
                continue
                
            try:
                # Get current background image
                current_image = xbmc.getInfoLabel(f'Control.GetLabel({self.container})')
                
                # If image changed, blur it
                if current_image and current_image != self._last_image:
                    log(f'BlurService: New image detected, blurring...')
                    self._blur_image(current_image)
                    self._last_image = current_image
                    
            except Exception as e:
                log(f'BlurService: Error - {e}', level='ERROR')
                
            # Sleep before next check
            xbmc.sleep(self.interval)
            
    def _blur_image(self, image_path):
        """
        Blur an image and set window properties.
        
        Args:
            image_path: Path to image to blur
        """
        try:
            # Create blur processor
            blur = ImageBlur(
                file=image_path,
                radius=self.radius,
                saturation=float(self.saturation)
            )
            
            # Set window properties for skin
            window = xbmcgui.Window(10000)
            window.setProperty('FlatscanBlurImage', blur.filepath)
            window.setProperty('FlatscanBlurColor', blur.avgcolor)
            
            log(f'BlurService: Blurred image set')
            
        except Exception as e:
            log(f'BlurService: Failed to blur image - {e}', level='ERROR')