############## INITIALIZATION ##############

import random
import pygame as pg
import easing_functions as easing
import draw
import time

pg.init()

# app size
windowx = 640
windowy = 360
# window size, changes on resize
screenx = 1280
screeny = 720
# screen aspect ratio x:y
ratiox = 16
ratioy = 9

clock = pg.time.Clock()
dfps = 0.0 # current fps
fps = 0    # target fps (0 - no limit)
td = 0.0   # timedelta
           # how much time passed between two frames
           # used to run the game independent of framerate

window = pg.display.set_mode((screenx,screeny), pg.RESIZABLE) # the window surface
screen = pg.Surface((windowx, windowy)) # the surface that everything gets
                                        # drawn on, this surface is then scaled
                                        # to fit in the window correctly and then gets
                                        # drawn to the window surface

running = True
pg.display.set_caption('game')
draw.def_surface = screen

halfx = windowx//2 # half of the X window size
halfy = windowy//2 # half of the Y window size


# app functions 

def draw_debug():
    '''
    Draws debug data on top of the screen.
    '''    
    draw.text(f'FPS: {dfps}', (0,0), (0,0,0))
    draw.text(f'FPS: {dfps}', (0,1))
    
    draw.text(f'Timedelta: {round(td,6)}', (0,8), (0,0,0))
    draw.text(f'Timedelta: {round(td,6)}', (0,9))

def update_size():
    '''
    This function updates the values of how the window
    is supposed to scale. Should be called when the window
    gets resized.
    '''
    global sizex, sizey, screenx, screeny, windowrect, windowrect_top

    if screenx/ratiox > screeny/ratioy:
        sizex = screeny/ratioy*ratiox
        sizey = screeny
    elif screeny/ratioy > screenx/ratiox:
        sizex = screenx
        sizey = screenx/ratiox*ratioy
    else:
        sizex = screenx
        sizey = screeny

    windowrect = pg.Rect(0,0,sizex, sizey)
    windowrect.center = (screenx/2, screeny/2)
    windowrect_top = windowrect.topleft


# app classes
    
class App:
    def __init__(self):
        pass

    def draw(self):
        draw.image('3s.png', mouse_pos, h=0.5, v=0.5)

    def update(self):
        pass


# app variables

app = App()
debug_opened = False


# preparation 
    
update_size()


# main loop

while running:
    # timedelta
    start_td = time.time()
    # input
    events = pg.event.get()
    global_mouse_pos = pg.mouse.get_pos() # mouse pos relative to the topleft of the window
    mouse_pos = [
        (global_mouse_pos[0]-windowrect_top[0])/(sizex/windowx),
        (global_mouse_pos[1]-windowrect_top[1])/(sizey/windowy)
    ] # mouse pos relative to the topleft of the "screen" variable
    mouse_press = pg.mouse.get_pressed(3)
    mouse_moved = pg.mouse.get_rel()
    keys = pg.key.get_pressed() # keys that are being held
    keysdown = [] # list of keys that are pressed in the current frame

    screen.fill((0,0,0))

    # events
    for event in events:
        if event.type == pg.QUIT:
            running = False 

        if event.type == pg.VIDEORESIZE:
            # resizing the window
            screenx = event.w
            screeny = event.h
            # limiting window dimensions
            if screenx <= windowx:
                screenx = windowx
            if screeny <= windowy:
                screeny = windowy
            # updating size
            update_size()
            window = pg.display.set_mode((screenx,screeny), pg.RESIZABLE)

        if event.type == pg.KEYDOWN:
            keysdown.append(event.key)
            if event.key == pg.K_F3:
                debug_opened = not debug_opened

    # drawing app
    app.update()
    app.draw()

    # drawing debug
    if debug_opened:
        draw_debug()

    # updating
    surface = pg.transform.scale(screen, (sizex, sizey))
    window.blit(surface, windowrect)
    pg.display.flip()
    clock.tick(fps)
    dfps = round(clock.get_fps(), 2)
    td = time.time()-start_td