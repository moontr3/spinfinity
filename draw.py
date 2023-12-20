# LIGRARIES
import glob
import pygame as pg
from typing import *


# CLASSES
class FontGroup:
    def __init__(self, font_folder:str):
        '''
        A class that manages all loaded fonts and
        saves the loaded objects for later use.
        '''
        self.font_folder: str = font_folder
        self.fonts: Dict[str, Dict[int, pg.font.Font]] = {}

    def init_font(self, size:int, style:str):
        '''
        Creates a new saved font object or replaces current
        with the new one.
        '''
        if style not in self.fonts:
            self.fonts[style] = {}
        self.fonts[style][size] =\
            pg.font.Font(self.font_folder+style+'.ttf', size)

    def find(self, size:int, style:str):
        '''
        Request the font object.

        If font is not loaded, creates a new saved font
        using `init_font` and returns it.
        '''
        if style in self.fonts:
            if size in self.fonts[style]:
                return self.fonts[style][size]
        
        self.init_font(size, style)
        return self.find(size, style)

class ImageType:
    def __init__(self, image_path:str):
        '''
        A class that manages a single image and
        saves the resized versions of the image for later use.
        '''
        self.image_path: str = image_path
        self.base_image: pg.Surface = pg.image.load(image_path).convert_alpha()
        self.base_image_size = self.base_image.get_size()
        self.resized_images: Dict[str, pg.Surface] = {}

    def param_to_str(self, size:Union[int, int], smooth:bool, fliph=False, flipv=False):
        '''
        Converts data used to request the image to `str` format.
        
        This is required for indexing in dicts.
        '''
        return str(int(smooth))+str(int(fliph))+str(int(flipv))+f'{size[0]},{size[1]}'
    
    def init_image(self, size:Union[int, int], smooth:bool, fliph:bool, flipv:bool, str_param:str):
        '''
        Resizes the base image and saves it for
        later use.
        '''
        func = pg.transform.scale if not smooth else pg.transform.smoothscale
        image = func(self.base_image, size)
        if fliph != False or flipv != False:
            image = pg.transform.flip(image, fliph, flipv)
        self.resized_images[str_param] = image

    def find(self, size:Union[int, int], smooth=True, fliph=False, flipv=False):
        '''
        Request the resized image.

        If the image was not resized yet (and thus not
        saved in the dictionary), resizes the image using
        `init_image` and returns it.
        '''
        if size == self.base_image_size:
            return self.base_image

        str_param = self.param_to_str(size, smooth, fliph, flipv)

        if str_param in self.resized_images:
            return self.resized_images[str_param]
        else:
            self.init_image(size, smooth, fliph, flipv, str_param)
            return self.find(size, smooth)

class ImageGroup:
    def __init__(self, image_folder:str):
        '''
        A class that manages all images inside a
        folder and all folders inside the parent
        folder recursively.
        '''
        self.image_folder: str = image_folder
        self.images: Dict[str, ImageType] = {}

    def init_image(self, image:str, image_path:str):
        '''
        Creates a new `ImageType` if it was not
        created yet.
        '''
        self.images[image] = ImageType(image_path)

    def find(self, image:str, size:Union[int,int], smooth=True, fliph=False, flipv=False):
        '''
        Request a resized image.
        
        If the image is not loaded yet, loads it using
        `init_image` and returns the correct image.
        '''
        if image in self.images:
            return self.images[image].find(size, smooth, fliph, flipv)
        else:
            self.init_image(image, self.image_folder+image)
            return self.find(image, size, smooth, fliph, flipv)

# INITIALIZING OBJECTS
pg.font.init()

fonts = FontGroup("res/fonts/")
images = ImageGroup("res/images/")

def_surface = None # default surface for drawing
                   # stuff. made this to not put the
                   # surface arg in every single draw
                   # call.


# TEXT DRAWING
def text(
        text='',
        pos=(0,0),
        color=(255,255,255), 
        size=6,
        style='regular', 
        h=0.0, 
        v=0.0, 
        antialias=True, 
        rotation=0,
        opacity=255,
        surface=None
    ):
    '''
    Draws text on the specified surface.
    '''

    # surface
    if surface == None:
        surface = def_surface

    # getting font
    font = fonts.find(size, style)
    rtext = font.render(text, antialias, color)

    # rotation
    if rotation != 0:
        rtext = pg.transform.rotate(rtext, rotation)

    # opacity
    if opacity != 255:
        rtext.set_alpha(opacity)

    # aligning
    btext = rtext.get_rect()
    btext.topleft = pos

    # shifting the image
    # both 0.0 = pos variable is topleft
    # both 0.5 = pos variable is the center
    # both 1.0 = pos variable is bottomright
    # you get the idea
    # same for the image function (too lazy to write this there)
    if h != 0.0:
        btext.x -= btext.size[0]*h
    if v != 0.0:
        btext.y -= btext.size[1]*v
    
    # drawing
    surface.blit(rtext, btext)
    return font.size(text)


# IMAGE DRAWING
def image(
        image:str,
        pos=(0,0),
        size=(48,48), 
        h=0.0, 
        v=0.0, 
        rotation=0,
        opacity=255,
        fliph=False,
        flipv=False,
        surface=None,
        smooth=True
    ):
    '''
    Draws an image on the specified surface.
    '''

    # surface
    if surface == None:
        surface = def_surface

    # getting image
    image = images.find(image, size, smooth, fliph, flipv)

    # rotation
    if rotation != 0:
        image = pg.transform.rotate(image, rotation)

    # opacity
    if opacity != 255:
        image.set_alpha(opacity)

    # aligning
    rect = image.get_rect()
    rect.topleft = pos

    # shifting the image
    # more in `text` func
    if h != 0.0:
        rect.x -= rect.size[0]*h
    if v != 0.0:
        rect.y -= rect.size[1]*v
    
    # drawing
    surface.blit(image, rect)


# TEXT SIZE
def get_text_size(text='', size=6, style='regular'):
    '''
    Returns the dimensions of the text in the specified font.
    '''
    font = fonts.find(size, style)
    return font.size(text)