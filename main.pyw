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

def rad2deg(angle:float):
    '''
    Converts radian to degrees.
    '''
    return (-np.rad2deg(angle)-90)%360

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
        '''
        Initial projectile data.
        '''
        self.image:str = data['image']
        self.size:Tuple[int,int] = data['size']
        self.speed:Tuple[int,int] = data['speed']
        self.slowdown: float = data['slowdown']
        self.lifetime: float = data['lifetime']

    def random_speed(self):
        return random.randint(self.speed[0], self.speed[1])

    def random_lifetime(self):
        return random.random()*(self.lifetime[1]-self.lifetime[0])+self.lifetime[0]


class Projectile:
    def __init__(self, projectile:ProjectileData, position:Tuple[int,int], angle:float):
        '''
        Projectile that will be displayed on screen.
        '''
        self.projectile: ProjectileData = projectile
        self.position: Tuple[int,int] = position
        self.angle = angle
        self.degrees_angle = rad2deg(angle)
        self.speed = projectile.random_speed()
        self.lifetime: float = projectile.random_lifetime()

        self.velocity: Tuple[float,float] = [
            np.cos(angle),
            np.sin(angle)
        ]

    def draw(self, position:Tuple[int,int]):
        '''
        Draws the projectile.
        '''
        draw.image(
            self.projectile.image,
            position,
            self.projectile.size,
            rotation=self.degrees_angle,
            h=0.5, v=0.5
        )

    def update(self):
        '''
        Updates the projectile.
        '''
        self.lifetime -= td

        self.speed -= self.projectile.slowdown*td

        self.position[0] += self.velocity[0]*self.speed*td
        self.position[1] += self.velocity[1]*self.speed*td


class WeaponData:
    def __init__(self, data:dict):
        '''
        Initial weapon data.
        '''
        self.name: str = data['name']
        self.image: str = data['image']
        self.speed: float = data['speed']
        self.projectile: ProjectileData = ProjectileData(data['projectile'])
        self.range: int = data['range']
        self.speed: float = data['speed']
        self.amount: int = data['amount']
        self.recoil: float = data['recoil']
        self.shake: float = data['shake']

    def random_range(self):
        return np.deg2rad(random.randint(-self.range, self.range))


class MapData:
    def __init__(self, data:dict):
        '''
        Used to represent map data.
        '''
        self.image:str = data['image']
        self.size: Tuple[int,int] = data['size']

        self.player_spawn: Tuple[int,int] = data['spawn']
        self.enemy_spawn_locations: List[Tuple[int,int]] = data['enemy_spawns']

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


class BulletDeath:
    def __init__(self, position):
        self.position = position
        self.key = 0.0

        self.deletable = False

    def draw(self, position:Tuple[int,int]):
        pg.draw.circle(
            screen,
            (200,200,200),
            position,
            int(self.key*10),
            int(max(1,self.inverse_key*10))
        )
        
    def update(self):
        self.key += td*4
        self.inverse_key = 1-self.key

        if self.key >= 1.0:
            self.deletable = True

    
class Dungeon:
    def __init__(self, weapon:WeaponData, player:PlayerData, map:MapData):
        '''
        The entire gameplay.
        '''
        # map and camers
        self.map: MapData = map

        self.cam_center = map.player_spawn
        self.cam_smoothed_center = [
            map.player_spawn[0],
            map.size[1]+10
        ]

        # player
        self.player: PlayerData = player
        self.player_pos: Tuple[float,float] = map.player_spawn
        self.player_vel: Tuple[float,float] = [0,0]
        self.player_health: int = player.health
        self.player_damage: int = player.damage
        self.available_stamina: float = player.stamina
        self.stamina_restore_timer: float = 0.0

        # projectiles and weapons
        self.projectiles: List[Projectile] = []
        self.weapon: WeaponData = weapon
        self.shooting_timer: float = 0.0

        # effects
        self.effects = []
        self.shakiness: float = 0.0
        self.shake_pos: Tuple[float,float] = [0,0]

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
            halfx-(self.cam_smoothed_center[0]-pos[0])*TILE_SIZE+self.shake_pos[0],
            halfy-(self.cam_smoothed_center[1]-pos[1])*TILE_SIZE+self.shake_pos[1]
        ]
    
    def draw_player(self):
        '''
        Draws the player.
        '''
        # mouse cursor
        draw.image(
            'cursor_bar.png',
            self.global_player_pos,
            (1,100),
            h=0.5,v=0.5,
            rotation=self.mouse_degrees_angle
        )

        # player
        draw.image(
            '3s.png',
            self.global_player_pos,
            h=0.5, v=0.5,
            fliph=self.mouse_degrees_angle<180
        )

        # weapon
        draw.image(
            self.weapon.image,
            self.global_player_pos,
            h=0.5, v=0.5,
            fliph=self.mouse_degrees_angle<180
        )


    def update_player(self):
        '''
        Updates the player.
        '''
        # checking if the player is moving rn
        moving = [i for i in [keys[pg.K_w], keys[pg.K_a], keys[pg.K_s], keys[pg.K_d]] if i]
        # calculating how fast should the player move
        speed = self.player.speed + (int(keys[pg.K_LSHIFT] and self.available_stamina > 0)*self.player.speed/1.5)
        # i'm too lazy to learn vectors so this is a 'cheat code'
        # on how to make the player walk diagonally with the same
        # speed as straight
        if len(moving) == 2:
            speed *= 0.77 # completely made up number
                          # no like fr i don't know what does this number mean

        # decreasing stamina when sprinting
        if keys[pg.K_LSHIFT] and moving and self.available_stamina > 0:
            self.available_stamina -= td
            self.stamina_restore_timer = 3
        # resting to restore stamina
        elif self.stamina_restore_timer > 0:
            self.stamina_restore_timer -= td
        # restoring stamina when rested
        elif self.available_stamina < self.player.stamina:
            self.available_stamina += td*2

        # moving player
        if moving:
            if keys[pg.K_w]:
                self.player_pos[1] -= speed*td
            if keys[pg.K_s]:
                self.player_pos[1] += speed*td
            if keys[pg.K_a]:
                self.player_pos[0] -= speed*td
            if keys[pg.K_d]:
                self.player_pos[0] += speed*td

        # making the player not go outside the map
        self.player_pos[0] = max(0.5, min(self.map.size[0]-0.5, self.player_pos[0]))
        self.player_pos[1] = max(0.5, min(self.map.size[1]-0.5, self.player_pos[1])) 

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
            i.draw(self.local_to_global(i.position))

        # effects
        for i in self.effects:
            i.draw(self.local_to_global(i.position))

        # player
        self.draw_player()

    def update(self):
        '''
        Updates the game.
        '''
        # updating cursor
        self.global_player_pos = self.local_to_global(self.player_pos)
        self.mouse_angle = np.arctan2(
            mouse_pos[1]-self.global_player_pos[1],
            mouse_pos[0]-self.global_player_pos[0]
        )
        self.mouse_degrees_angle = rad2deg(self.mouse_angle)

        # shakiness
        if self.shakiness > 0.0:
            self.shake_pos = [(random.random()*2-1)*self.shakiness for i in range(2)]
            self.shakiness = lerp(self.shakiness, 0, 8*td)
            if self.shakiness < 0.0:
                self.shakiness = 0.0

        # smooth camera
        self.cam_smoothed_center[0] = lerp(self.cam_smoothed_center[0], self.cam_center[0], 6*td)
        self.cam_smoothed_center[1] = lerp(self.cam_smoothed_center[1], self.cam_center[1], 6*td)

        self.cam_center = [self.player_pos[0],self.player_pos[1]]

        # shooting
        if self.shooting_timer > 0.0:
            self.shooting_timer -= td

        if mouse_press[0]:
            while self.shooting_timer <= 0.0:
                # spawning projectiles
                for i in range(self.weapon.amount):
                    self.projectiles.append(Projectile(
                        self.weapon.projectile,
                        [self.player_pos[0], self.player_pos[1]],
                        self.mouse_angle+self.weapon.random_range()
                    ))
                self.shooting_timer += self.weapon.speed
                # shaking and recoil
                self.shakiness += self.weapon.shake
                relative = [np.cos(self.mouse_angle),np.sin(self.mouse_angle)]
                self.player_pos[0] -= relative[0]*self.weapon.recoil
                self.player_pos[1] -= relative[1]*self.weapon.recoil

        # projectiles
        new = []
        for i in self.projectiles:
            i.update()
            if not ( # keeping projectile if not out of bounds
                (i.position[0] < 0.0 or i.position[1] < 0.0) or\
                (i.position[0] > self.map.size[0] or i.position[1] > self.map.size[1])
            ) and ( # and if lifetime has not ran out yet
                i.lifetime > 0.0 
            ):
                new.append(i)
            else: # not keeping the projectile
                self.effects.append(BulletDeath(i.position))
        self.projectiles = new

        # updating player
        self.update_player()

        # effects
        new = []
        for i in self.effects:
            i.update()
            if not i.deletable:
                new.append(i)
        self.effects = new


# app variables

app = Dungeon(
    WeaponData({
        'name':       'Shotgun',
        'image':      '3s.png',
        'speed':      0.5,
        'range':      15,
        'amount':     6,
        'recoil':     0.25,
        'shake':      3,
        'projectile': {
            'image':    '3s.png',
            'size':     [16,16],
            'speed':    [15,20],
            'slowdown': 4,
            'lifetime': [0.5, 0.6]
        }
    }),
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