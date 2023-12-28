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

pg.mouse.set_visible(False)
running = True
pg.display.set_caption('game')
draw.def_surface = screen

halfx = windowx//2 # half of the X window size
halfy = windowy//2 # half of the Y window size


# constants

TILE_SIZE = 32


# app functions 

def rad2deg(angle:float) -> float:
    '''
    Converts radian to degrees.
    '''
    return (-np.rad2deg(angle)-90)%360

def points_to_angle(p1: Tuple[float,float], p2: Tuple[float,float]) -> float:
    '''
    Returns angle between two points in radians.
    '''
    return np.arctan2(
        p2[1]-p1[1],
        p2[0]-p1[0]
    )

def get_distance(p1: Tuple[float,float], p2: Tuple[float,float]) -> float:
    '''
    Returns distance between two 2D points.
    '''
    return ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)**0.5

def lerp(a:float, b:float, t:float) -> float:
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

    # calculating the size of the screen
    if screenx/ratiox > screeny/ratioy:
        sizex = screeny/ratioy*ratiox
        sizey = screeny
    elif screeny/ratioy > screenx/ratiox:
        sizex = screenx
        sizey = screenx/ratiox*ratioy
    else:
        sizex = screenx
        sizey = screeny

    # updating rect of the screen
    windowrect = pg.Rect(0,0,sizex, sizey)
    windowrect.center = (screenx/2, screeny/2)
    windowrect_top = windowrect.topleft


# app classes

class ProjectileData:
    def __init__(self, data:dict):
        '''
        Initial projectile data.
        '''
        self.image:str = data['image'] # projectile image
        self.size:Tuple[int,int] = data['size'] # projectile size in pixels
        self.speed:Tuple[int,int] = data['speed'] # projectile speed px/s
                                                  # first value is the minimum and
                                                  # the second is the maximum
        self.slowdown: float = data['slowdown'] # how much the projectile slows down per second
        self.lifetime: Tuple[int,int] = data['lifetime'] # projectile lifetime in seconds
                                                         # first value is the minimum and
                                                         # the second is the maximum
        self.hit_type: str = data['hit'] # who the projectile can damage
                                         # can either be "player" or "enemy"
        self.damage: Tuple[int,int] = data['damage'] # bullet damage
                                                     # first value is the minimum and
                                                     # the second is the maximum

    def random_speed(self) -> int:
        '''
        Returns randomly generated speed
        between two provided values.
        '''
        return random.randint(self.speed[0], self.speed[1])

    def random_lifetime(self) -> float:
        '''
        Returns randomly generated lifetime
        between two provided values.
        '''
        return random.random()*(self.lifetime[1]-self.lifetime[0])+self.lifetime[0]

    def random_damage(self) -> int:
        '''
        Returns randomly generated damage
        between two provided values.
        '''
        return random.randint(self.damage[0], self.damage[1])


class Projectile:
    def __init__(self, projectile:ProjectileData, position:Tuple[int,int], angle:float):
        '''
        Projectile that will be displayed on screen.
        '''
        self.projectile: ProjectileData = projectile
        self.position: Tuple[int,int] = position
        self.angle = angle # angle in radians
        self.degrees_angle = rad2deg(angle) # angle in degrees
        self.speed = projectile.random_speed() # current speed px/s
        self.lifetime: float = projectile.random_lifetime() # lifetime left in seconds
        self.damage: int = projectile.random_damage() # how much damage projectile has

        self.velocity: Tuple[float,float] = [ # X and Y velocities of the projectile
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
        self.name: str = data['name'] # weapon name
        self.image: str = data['image'] # weapon image
        self.size: Tuple[int,int] = data['size'] # weapon image size in pixels
        self.speed: float = data['speed'] # what time has to pass between two shots in seconds
        self.range: int = data['range'] # maximum shooting range in degrees
        self.amount: int = data['amount'] # amount of projectiles to spawn when shot
        self.recoil: float = data['recoil'] # how much the player gets pushed back when shot in units
        self.shake: float = data['shake'] # how much the screen should shake
        self.projectile: ProjectileData = ProjectileData(data['projectile'])

    def random_range(self) -> float:
        '''
        Returns randomly generated shooting
        range between `-range` and `range` as radians.
        '''
        return np.deg2rad(random.randint(-self.range, self.range))


class MapData:
    def __init__(self, data:dict):
        '''
        Used to represent map data.
        '''
        self.image:str = data['image'] # map image
        self.size: Tuple[int,int] = data['size'] # map size in units

        self.player_spawn: Tuple[int,int] = data['spawn'] # where the player should spawn in units
        self.enemy_spawn_locations: List[Tuple[int,int]] = data['enemy_spawns']
            # list of enemy spawn locations in unit coordinates

        self.pixel_size = [ # size of the map in pixels
            self.size[0]*TILE_SIZE,
            self.size[1]*TILE_SIZE
        ]
        

class PlayerData:
    def __init__(self, data:dict):
        '''
        Used to represent player data.
        '''
        self.image: str = data['image'] # player sprite
        self.speed: float = data['speed'] # player speed units/s
        self.health: int = data['health'] # player base health
        self.stamina: int = data['stamina'] # player base stamina
        self.u_points: int = data['upoints'] # amount of points needed to reach ultimate


class EnemyData:
    def __init__(self, data:dict):
        '''
        Used to represent enemy data.
        '''
        self.image: str = data['image'] # enemy sprite
        self.size: Tuple[int,int] = data['size'] # size of sprite in pixels
        self.speed: float = data['speed'] # enemy speed units/s
        self.health: int = data['health'] # enemy base health
        self.damage: ProjectileData = ProjectileData(data['projectile']) # enemy projectile


class BulletDeath:
    def __init__(self, position=Tuple[int,int]):
        self.position: Tuple[int,int] = position
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


class Enemy:
    def __init__(self, enemy:EnemyData, position:Tuple[int,int]):
        self.enemy: EnemyData = enemy
        self.position: Tuple[int,int] = position
        self.size: Tuple[int,int] = (
            self.enemy.size[0]/TILE_SIZE,
            self.enemy.size[1]/TILE_SIZE
        ) # size of enemy rect in units
        self.update_rect()

        self.health: int = enemy.health
        self.direction_angle: float = 0.0 # direction the enemy is facing in radians
        self.glow_key: float = 0.0

    def hit(self, damage:int):
        '''
        This function gets called when the
        enemy is hit by a projectile.
        '''
        self.health -= damage
        self.glow_key = 1.0

    def update_path(self, player_pos:Tuple[float,float], enemies:List):
        '''
        Updates the direction angle of self
        in place according to the provided data.
        '''
        self.direction_angle = points_to_angle(self.position,player_pos)
        # keeping the enemies at a certain distance
        # from each other so they don't form a big blob
        if len(enemies) != 0:
            for i in enemies:
                # if i.rect.colliderect(self.rect):
                distance = get_distance(self.position, i.position)
                angle = points_to_angle(self.position, i.position)
                self.position[0] -= np.cos(angle)*(1/distance)*0.001
                self.position[1] -= np.sin(angle)*(1/distance)*0.001

    def update_rect(self):
        '''
        Updates the enemy rect in place.
        '''
        self.rect = pg.Rect((0,0), self.size)
        self.rect.center = self.position

    def draw(self, position: Tuple[int,int]):
        '''
        Draws the enemy at the desired
        position.
        '''
        # image
        draw.image(
            self.enemy.image,
            position,
            self.enemy.size,
            h=0.5, v=0.5
        )
        # hp bar
        draw.text(
            f'{self.health} HP',
            (position[0],position[1]-self.enemy.size[1]/2),
            h=0.5, v=2
        )
        # glow
        if self.glow_key > 0.0:
            for i in range(int(self.glow_key*2)+1):
                draw.image(
                    self.enemy.image,
                    position,
                    self.enemy.size,
                    h=0.5, v=0.5,
                    blending=pg.BLEND_RGBA_ADD 
                ) # blending doesn't support opacity so my solution
                  # is drawing the same image over and over again
                  # with the same opacity and gradually decreasing
                  # the amount of images being drawn to create an 
                  # illusion of smooth fading

    def update(self):
        '''
        Updates the enemy.
        '''
        self.position[0] += np.cos(self.direction_angle)*self.enemy.speed*td
        self.position[1] += np.sin(self.direction_angle)*self.enemy.speed*td

        if self.glow_key > 0:
            self.glow_key -= td*10
            if self.glow_key < 0:
                self.glow_key = 0

        self.update_rect()

    
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
        self.available_stamina: float = player.stamina
        self.stamina_restore_timer: float = 0.0

        # projectiles and weapons
        self.projectiles: List[Projectile] = []
        self.weapon: WeaponData = weapon
        self.shooting_timer: float = 0.0

        # enemies
        self.enemies: List[Enemy] = [Enemy(EnemyData({
            'image':      '3s.png',
            'size':       [32,32],
            'speed':      3.0,
            'health':     250,
            'damage':     9,
            'crit':       1.25,
            'projectile': {
                'image':    '3s.png',
                'size':     [10,10],
                'speed':    [15,20],
                'slowdown': 10,
                'lifetime': [0.9, 1],
                'hit':      'player',
                'damage':   400
            }
        }), [random.randint(1,19), random.randint(1,9)]) for i in range(10)]

        # effects
        self.effects: list = []
        self.shakiness: float = 0.0
        self.shake_pos: Tuple[float,float] = [0,0]

        # stats
        self.score: int = 0
        self.points: int = 0
        self.level: int = 0
        self.kills: int = 0
        self.kills_to_next_level: int = 5


    def get_enemy_projectiles(self) -> List[Projectile]:
        return [i for i in self.projectiles if i.projectile.hit_type == 'enemy']

    def get_player_projectiles(self) -> List[Projectile]:
        return [i for i in self.projectiles if i.projectile.hit_type == 'player']


    def local_to_global(self, pos) -> Tuple[float,float]:
        '''
        Converts map coordinates to coordinates on screen.

        Even I don't know what's all this math already.
        '''
        return [
            halfx-(self.cam_smoothed_center[0]-pos[0])*TILE_SIZE+self.shake_pos[0],
            halfy-(self.cam_smoothed_center[1]-pos[1])*TILE_SIZE+self.shake_pos[1]
        ]
    

    def damage_player(self, amount:int):
        self.player_health -= amount
    
    
    def draw_ui(self):
        '''
        Draws the HUD.
        '''
        # mouse crosshair
        draw.image(
            'crosshair.png',
            mouse_pos,
            (11,11),
            h=0.5,v=0.5,
        )
    

    def draw_player(self):
        '''
        Draws the player.
        '''
        # cursor pointer
        draw.image(
            'cursor_bar.png',
            self.global_player_pos,
            (1,150*(1-self.shooting_timer/self.weapon.speed)),
            h=0.5,v=0.5,
            rotation=self.mouse_degrees_angle
        )

        # player
        draw.image(
            self.player.image,
            self.global_player_pos,
            (TILE_SIZE,TILE_SIZE),
            h=0.5, v=0.5,
            fliph=self.mouse_degrees_angle<180,
            smooth=False
        )

        # weapon
        draw.image(
            self.weapon.image,
            self.global_player_pos,
            self.weapon.size,
            h=0.5, v=0.5,
            rotation=self.mouse_degrees_angle,
            flipv=self.mouse_degrees_angle<180
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

            self.player_rect = pg.Rect((0,0),(TILE_SIZE,TILE_SIZE))
            self.player_rect.center = self.player_pos

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

        # enemies
        for i in self.enemies:
            i.draw(self.local_to_global(i.position))

        # player
        self.draw_player()
        
        # ui
        self.draw_ui()


    def update(self):
        '''
        Updates the game.
        '''
        # updating cursor
        self.global_player_pos = self.local_to_global(self.player_pos)
        self.mouse_angle = points_to_angle(self.global_player_pos,mouse_pos)
        self.mouse_degrees_angle = rad2deg(self.mouse_angle)

        # shakiness
        if self.shakiness > 0.0:
            self.shake_pos = [(random.random()*2-1)*self.shakiness for i in range(2)]
            self.shakiness = lerp(self.shakiness, 0, 8*td)
            if round(self.shakiness,1) == 0.0:
                self.shakiness = 0.0
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


        # updating player
        self.update_player()

        # projectiles
        new = []
        for i in self.projectiles:
            destroy = False # changes to True below if needed to delete the projectile
            fx = True # changes to True below if not needed to spawn the BulletDeath
            i.update()

            if not ( # keeping projectile if not out of bounds
                (i.position[0] < 0.0 or i.position[1] < 0.0) or\
                (i.position[0] > self.map.size[0] or i.position[1] > self.map.size[1])
            ) and ( # and if lifetime has not ran out yet
                i.lifetime > 0.0 
            ):
                pass
            else: # not keeping the projectile
                destroy = True

            # damaging player
            if i.projectile.hit_type == 'player':
                if self.player_rect.collidepoint(i.position):
                    destroy = True
                    fx = False
                    self.damage_player(i.damage)

            # damaging enemies
            if i.projectile.hit_type == 'enemy':
                for enemy in self.enemies:
                    if enemy.rect.collidepoint(i.position):
                        destroy = True
                        fx = False
                        enemy.hit(i.damage)
                
            # destroying the projectile if needed
            if not destroy:
                new.append(i)
            elif fx:
                self.effects.append(BulletDeath(i.position))


        self.projectiles = new

        # enemies
        new = []
        for i in self.enemies:
            # damage (damaging is actually done above,
            # we just remove unneeded enemy objects here)
            if i.health <= 0:
                continue

            # updating
            i.update_path(self.player_pos, [j for j in self.enemies if j.position != i.position])
            i.update()
            new.append(i)
        self.enemies = new

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
        'size':       [16,16],
        'speed':      0.05,
        'range':      15,
        'amount':     8,
        'recoil':     0.05,
        'shake':      1,
        'projectile': {
            'image':    '3s.png',
            'size':     [14,14],
            'speed':    [10,15],
            'slowdown': 5,
            'lifetime': [0.4, 0.6],
            'hit':      'enemy',
            'damage':   [3,5]
        }
    }),
    PlayerData({
        'image':   'chibi.png',
        'speed':   7,
        'health':  400,
        'crit':    1.25,
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
    keysdown = [] # list of keys that are just pressed in the current frame

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
    surface = pg.transform.scale(screen, (sizex, sizey)) # scaling the surface
    window.blit(surface, windowrect) # drawing the surface on screen
    pg.display.flip()
    clock.tick(fps)
    dfps = round(clock.get_fps(), 2) # getting fps
    td = time.time()-start_td # calculating timedelta for the next frame