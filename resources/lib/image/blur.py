#!/usr/bin/python
# coding: utf-8

"""
Image blur functionality.
"""

import os
import xbmc
import xbmcvfs
from PIL import ImageFilter, Image, ImageOps, ImageEnhance
from resources.lib.addon import ADDON_DATA_IMG_PATH
from resources.lib.logger import log


class ImageBlur:
    """
    Blur an image and cache the result.
    """
    
    def __init__(self, file=None, radius=20, saturation=1.0, prop='output'):
        """
        Initialize blur processor.
        
        Args:
            file: Image file path (if None, gets from skin container)
            radius: Blur radius
            saturation: Color saturation multiplier
            prop: Property prefix for output
        """
        self.image_path = file or self._get_skin_image()
        self.radius = radius
        self.saturation = saturation
        self.prop = prop
        
        if self.image_path:
            self.filepath = self._blur_image()
            self.avgcolor = self._get_average_color()
        else:
            self.filepath = ''
            self.avgcolor = 'FFF0F0F0'
            
    def _get_skin_image(self):
        """Get image from skin container."""
        container = xbmc.getInfoLabel('Skin.String(BlurContainer)') or '100000'
        return xbmc.getInfoLabel(f'Control.GetLabel({container})')
        
    def _blur_image(self):
        """Apply blur effect and save."""
        import hashlib
        
        # Create filename based on image path and settings
        img_hash = hashlib.md5(self.image_path.encode()).hexdigest()
        filename = f"{img_hash}_{self.radius}_{self.saturation}.png"
        output_path = os.path.join(ADDON_DATA_IMG_PATH, filename)
        
        # Return cached if exists
        if os.path.exists(output_path):
            return output_path
            
        try:
            # Open and process image
            img = Image.open(xbmcvfs.translatePath(self.image_path))
            
            # Resize for faster processing
            img.thumbnail((200, 200), Image.LANCZOS)
            
            # Convert to RGB
            img = img.convert('RGB')
            
            # Apply blur
            img = img.filter(ImageFilter.GaussianBlur(self.radius))
            
            # Apply saturation
            if self.saturation != 1.0:
                enhancer = ImageEnhance.Color(img)
                img = enhancer.enhance(self.saturation)
                
            # Save
            img.save(output_path)
            
            return output_path
            
        except Exception as e:
            log(f'Blur failed: {e}', level='ERROR')
            return ''
            
    def _get_average_color(self):
        """Get average color of blurred image."""
        try:
            img = Image.open(self.filepath)
            img_small = img.resize((1, 1), Image.LANCZOS)
            r, g, b = img_small.getpixel((0, 0))
            return f'FF{r:02x}{g:02x}{b:02x}'
        except:
            return 'FFF0F0F0'