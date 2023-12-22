############## INITIALIZATION ##############

import random
import pygame as pg
import easing_functions as easing
import draw
import time
from typing import *
import numpy as np

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


# constants

TILE_SIZE = 32


# app functions 

def lerp(a:float, b:float, t:float):
    '''
    Interpolates between A and B.
    '''
    t = max(0,min(1,t))
    return (1 - t) * a + t * b

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

class ProjectileData:
    def __init__(self, data:dict):
        self.image:str = data['image']
        self.size:Union[int,int] = data['size']
        self.speed:float = data['speed']


class Projectile:
    def __init__(self, projectile:ProjectileData, position:Union[int,int], angle:float):
        self.projectile: ProjectileData = projectile
        self.position: Union[int,int] = position
        self.angle = angle

        self.velocity: Union[float,float] = [
            np.cos(angle)*self.projectile.speed,
            np.sin(angle)*self.projectile.speed
        ]

    def update(self):
        self.position[0] += self.velocity[0]*td
        self.position[1] += self.velocity[1]*td


class MapData:
    def __init__(self, data:dict):
        '''
        Used to represent map data.
        '''
        self.image:str = data['image']
        self.size: Union[int,int] = data['size']

        self.player_spawn: Union[int,int] = data['spawn']
        self.enemy_spawn_locations: List[Union[int,int]] = data['enemy_spawns']

        self.pixel_size = [
            self.size[0]*TILE_SIZE,
            self.size[1]*TILE_SIZE
        ]
        

class PlayerData:
    def __init__(self, data:dict):
        '''
        Used to represent player data.
        '''
        self.speed = data['speed']
        self.health = data['health']
        self.damage = data['damage']
        self.stamina = data['stamina']
        self.u_points = data['upoints'] # amount of points needed to reach ultimate

    
class Dungeon:
    def __init__(self, player:PlayerData, map:MapData):
        '''
        The entire gameplay.
        '''
        # map and camers
        self.map: MapData = map

        self.cam_center = map.player_spawn
        self.cam_smooth = [
            map.player_spawn[0],
            map.size[1]+10
        ]

        # player
        self.player: PlayerData = player
        self.position: Union[float,float] = map.player_spawn
        self.velocity: Union[float,float] = [0,0]
        self.health: int = player.health
        self.damage: int = player.damage
        self.stamina: float = player.stamina
        self.stamina_restore: float = 0.0

        # projectiles
        self.projectiles: List[Projectile] = []
        self.player_proj = ProjectileData({
            'image': '3s.png',
            'size':  [16,16],
            'speed': 10
        })
        
        # stats
        self.score: int = 0
        self.points: int = 0
        self.level: int = 0
        self.kills: int = 0
        self.kills_to_next_level: int = 5


    def local_to_global(self, pos):
        '''
        Converts map coordinates to coordinates on screen.

        Even I don't know what's all this math already.
        '''
        return [
            halfx-(self.cam_smooth[0]-pos[0])*TILE_SIZE,
            halfy-(self.cam_smooth[1]-pos[1])*TILE_SIZE
        ]
    
    def update_player(self):
        '''
        Updates the player.
        '''
        # checking if the player is moving rn
        moving = [i for i in [keys[pg.K_w], keys[pg.K_a], keys[pg.K_s], keys[pg.K_d]] if i]
        # calculating how fast should he move
        speed = self.player.speed + (int(keys[pg.K_LSHIFT] and self.stamina > 0)*self.player.speed/1.5)
        # i'm too lazy to learn vectors so this is a 'cheat code'
        # on how to make the player walk diagonally with the same
        # speed as straight
        if len(moving) == 2:
            speed *= 0.77 # completely made up number
                          # no like fr i don't know what does this number mean

        # decreasing stamina when sprinting
        if keys[pg.K_LSHIFT] and moving and self.stamina > 0:
            self.stamina -= td
            self.stamina_restore = 3
        # resting to restore stamina
        elif self.stamina_restore > 0:
            self.stamina_restore -= td
        # restoring stamina when rested
        elif self.stamina < self.player.stamina:
            self.stamina += td*2

        # moving player
        if moving:
            if keys[pg.K_w]:
                self.position[1] -= speed*td
            if keys[pg.K_s]:
                self.position[1] += speed*td
            if keys[pg.K_a]:
                self.position[0] -= speed*td
            if keys[pg.K_d]:
                self.position[0] += speed*td

            # making the player not go outside the map
            self.position[0] = max(0.5, min(self.map.size[0]-0.5, self.position[0]))
            self.position[1] = max(0.5, min(self.map.size[1]-0.5, self.position[1])) 

    def draw(self):
        '''
        Draws everything.
        '''
        # map
        draw.image(
            self.map.image,
            self.local_to_global((0,0)),
            self.map.pixel_size
        )

        # projectiles
        for i in self.projectiles:
            draw.image(
                i.projectile.image,
                self.local_to_global(i.position),
                i.projectile.size,
                h=0.5, v=0.5
            )

        # player
        draw.image(
            '3s.png',
            self.local_to_global(self.position),
            h=0.5, v=0.5
        )

    def update(self):
        '''
        Updates the game.
        '''
        # updating cursor
        player_pos = self.local_to_global(self.position)
        self.mouse_angle = np.arctan2(
            mouse_pos[1]-player_pos[1],
            mouse_pos[0]-player_pos[0]
        )

        # smooth camera
        self.cam_smooth[0] = lerp(self.cam_smooth[0], self.cam_center[0], 3*td)
        self.cam_smooth[1] = lerp(self.cam_smooth[1], self.cam_center[1], 3*td)

        self.cam_center = [self.position[0],self.position[1]]

        # updating player
        self.update_player()

        # shooting
        if keys[pg.K_SPACE]:
            self.projectiles.append(Projectile(
                self.player_proj,
                [self.position[0], self.position[1]],
                self.mouse_angle
            ))

        # projectiles
        for i in self.projectiles:
            i.update()


# app variables

app = Dungeon(
    PlayerData({
        'speed':   7,
        'health':  400,
        'damage':  1.2,
        'stamina': 7,
        'upoints': 25000
    }),
    MapData({
        'image':        'maps/map1.png',
        'size':         [20,10],
        'spawn':        [10,5],
        'enemy_spawns': [[1,8], [18,1], [18,8], [1,1]]
    })
)
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
        # quitting the game
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

        # registering pressed keys
        if event.type == pg.KEYDOWN:
            keysdown.append(event.key)
            # enabling/disabling debug mode
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