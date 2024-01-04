'''

!! WARNING !!

This project requires
pygame-ce to run.

pip uninstall pygame
pip install pygame-ce

'''


import random
import pygame as pg
import draw
import time
from typing import *
import numpy as np
import easing_functions as easing
import json
import glob

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
dfps = 0.0       # current fps
prev_dfps = 0.0  # previous fps
fps = 0          # target fps (0 - no limit)
td = 0.0         # timedelta
                 # how much time passed between two frames
                 # used to run the game independent of framerate
halfpi = np.pi/2 # half of pi

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

def load_datapack(filename:str):
    '''
    Returns `Datapack` object by file path.
    '''
    with open(filename, encoding='utf-8') as f:
        return Datapack(json.load(f))
    
def load_datapacks(path:str):
    '''
    Returns a dict of Datapack objects with
    filenames as keys and Datapack objects
    as values.
    '''
    out = dict()
    path = path.rstrip('\\/')+'/'

    for i in glob.glob(path+'*.json'):
        i = i.replace('\\','/')
        out[i.removeprefix(path).removesuffix('.json')] = load_datapack(i)

    return out

def refresh_datapacks():
    '''
    Reloads all datapacks.
    '''
    global datapack, datapacks
    datapacks = load_datapacks('datapacks/')
    datapacks['Default'] = load_datapack('res/datapack.json')
    datapack = datapacks['Default']


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

def shorten(number:int, capitalize=False):
    abbr = ['', 'k','m','b','t','q']
    if capitalize:
        abbr = [i.upper() for i in abbr]

    for x in abbr:
        if number < 1000:
            return f"{round(number, 2)}{x}"
        number /= 1000

    return str(number*1000)+abbr[-1]

def draw_debug():
    '''
    Draws debug data on top of the screen.
    '''    
    # fps graph
    if dfps != prev_dfps:
        fps_graph.append(dfps)
    if len(fps_graph) > windowx:
        fps_graph.pop(0)
    if len(fps_graph) >= 2:
        pg.draw.lines(screen, (255,255,255), False, [(i,windowy-val/2) for i, val in enumerate(fps_graph)])

    # text
    draw.text(f'FPS: {dfps}{f" / {fps}" if fps != 0 else ""}', (0,1), shadows=[(0,-1)])
    draw.text(f'Timedelta: {round(td,6)}', (0,9), shadows=[(0,-1)])

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


# other classes

class Datapack:
    def __init__(self, data:dict):
        '''
        Game datapack - weapon info, maps, player etc.
        '''
        self.weapons: List[WeaponData] =\
            [WeaponData(i) for i in data['weapons']] # list of available weapons
                                                     # player will be given the first weapon
                                                     # on this list upon beginning session
        self.waves: List[WaveData] = [WaveData(i) for i in data['waves']] # list of available difficulties
        
        self.player: PlayerData = PlayerData(data['player'])


# game classes
        
class Animation:
    def __init__(self, frames: List[str], speed: float):
        '''
        A sequence of images.
        '''
        self.frames: List[str] = frames # list of frames that animation will play
        self.speed: float = speed # time between two frames per second
        self.current_time: float = 0.0 # timer used to switch animations
        self.frame: int = 0 # current animation frame

    @property
    def image(self) -> str:
        '''Returns the current frame.'''
        return self.frames[self.frame]

    def reset(self):
        '''
        Resets the animation.
        '''
        self.frame = 0
        self.current_time = 0.0

    def update(self):
        '''
        Updates the animation.
        '''
        self.current_time += td
        # switching frames
        while self.current_time > self.speed:
            self.current_time -= self.speed
            self.frame += 1
            if self.frame >= len(self.frames):
                self.frame = 0


class Animator:
    def __init__(self, animations:Dict[str, Animation], default:str):
        self.animations: Dict[str, Animation] = animations # all animations
        self.current: str = default # key of current animation

    @property
    def animation(self) -> Animation:
        '''Returns current animation.'''
        return self.animations[self.current]
    
    @property
    def image(self) -> str:
        '''Returns current frame of current animation.'''
        return self.animation.image

    def set_animation(self, new:str):
        '''
        Switches the animation to a new one.
        '''
        if self.current == new:
            return # not resetting the animation if it didn't change
        
        self.current = new
        self.animation.reset()

    def update(self):
        '''
        Updates the animator and the current animation.
        '''
        self.animation.update()


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
        self.speed: float = data['speed'] # player speed units/s
        self.health: int = data['health'] # player base health
        self.stamina: int = data['stamina'] # player base stamina
        self.anim: Animator = Animator({
            'stand': Animation(
                [i.removeprefix('res\\images\\') for i in glob.glob('res\\images\\player\\stand*.png')],
                0.4
            ),
            'walk': Animation(
                [i.removeprefix('res\\images\\') for i in glob.glob('res\\images\\player\\walk*.png')],
                0.05
            ),
        }, 'stand') # player animation


class EnemyData:
    def __init__(self, data:dict):
        '''
        Used to represent enemy data.
        '''
        self.image: str = data['image'] # enemy sprite
        self.size: Tuple[int,int] = data['size'] # size of sprite in pixels
        self.speed: float = data['speed'] # enemy speed units/s
        self.health: int = data['health'] # enemy base health
        self.projectile: ProjectileData = ProjectileData(data['projectile']) # enemy projectile
        self.weapon_speed: float = data['weaponspeed'] # time between firing two shots in seconds 
        self.range: int = data['range'] # maximum shooting range in degrees
        self.amount: int = data['amount'] # amount of projectiles spawned when fired
        self.cost: Tuple[int,int] = data['cost'] # how much killing the enemy gives

    def random_cost(self) -> int:
        '''
        Returns randomly generated cost
        between two values.
        '''
        return random.randint(self.cost[0], self.cost[1])

    def random_range(self) -> int:
        '''
        Returns randomly generated range
        between `-range` and `range`.
        '''
        return np.deg2rad(random.randint(-self.range, self.range))
    

class WaveEnemy:
    def __init__(self, data:dict):
        '''
        Enemy data that gets loaded from the datapack file.
        '''
        self.wave_start: Tuple[int,int] = data['wave_start'] # the wave this enemy starts to appear on
        self.amount_start: Tuple[int,int] = data['amount_start'] # the amount of enemies spawned
                                                                 # on the first time
        self.amount_end: Tuple[int,int] = data['amount_end'] # maximum amount of enemies that can spawn in one wave
        self.amount_increase: Tuple[int,int] = data['amount_increase'] # how much the total max amount gets
                                                                       # increased every wave
        self.enemy: EnemyData = EnemyData(data['enemy']) # enemy data
    

class WaveData:
    def __init__(self, data:dict):
        '''
        Wave data a.k.a. game difficulty.
        '''
        self.name: str = data['name'] # difficulty name
        self.spawn_delay: Tuple[float,float] = data['spawn_delay'] # range of time between
                                                                   # spawning two enemies
        self.limit_start: Tuple[int,int] = data['limit_start'] # maximum amount of enemies on field
                                                               # at the start of the session
        self.limit_increase: Tuple[int,int] = data['limit_increase'] # how much the above limit
                                                                     # increases every wave
        self.limit_end: int = data['limit_end'] # maximum amount of enemies on field
        self.boss_every: int = data['boss_every']
        self.enemies: List[WaveEnemy] =\
            [WaveEnemy(i) for i in data['enemies']] # list of modifiable enemies that can spawn
        self.bosses: List[EnemyData] =\
            [EnemyData(i) for i in data['bosses']] # list of boss enemies
        
    def random_boss(self) -> EnemyData:
        '''
        Returns a random boss enemy.
        '''
        return random.choice(self.bosses)
        

class EnemyType:
    def __init__(self, enemy:WaveEnemy):
        '''
        An enemy type for a session. Used in
        QueueManager to select enemies for the 
        next wave.

        Basically chooses random values and settles
        on them for the rest of the session.
        '''
        self.enemy: WaveEnemy = enemy # original WaveEnemy object
        self.wave: int = 0 # current wave number
        self.begin_at: int = random.randint(*enemy.wave_start) # the wave number when to begin spawning the enemies
        self.amount: int = random.randint(*enemy.amount_start) # initial amount to spawn in one wave
        self.max_amount: int = random.randint(*enemy.amount_end) # maximum amount that can spawn in one wave

    def random_increase(self):
        '''
        Returns how much the amount should increase.
        '''
        return random.randint(*self.enemy.amount_increase)
    
    def step(self):
        self.wave += 1
        if self.wave > self.begin_at:
            self.amount += self.random_increase()

    def get_amount(self):
        if self.begin_at > self.wave:
            return 0
        return self.amount
        

class QueueManager:
    def __init__(self, data:WaveData):
        '''
        An object to store
        '''
        self.data: WaveData = data
        self.wave: int = 0
        self.enemies: List[EnemyType] = [EnemyType(i) for i in data.enemies]

    def step(self):
        '''
        Steps one wave forward.
        '''
        self.wave += 1
        for i in self.enemies:
            i.step()

    def gen_queue(self) -> List[EnemyData]:
        '''
        Generates a queue for currently
        stored wave data.
        '''
        out = []
        for enemy in self.enemies:
            for i in range(enemy.get_amount()):
                out.append(enemy.enemy.enemy)

        random.shuffle(out)
        return out


class Effect:
    def __init__(self):
        self.deletable: bool = False

    def draw(self, position:Tuple[int,int]):
        pass

    def update(self):
        pass


class BulletDeath(Effect):
    def __init__(self, position=Tuple[int,int]):
        '''
        Used to represent a particle that is
        displayed when the bullet hits a wall or
        naturally despawns.
        '''
        super().__init__()
        self.position: Tuple[int,int] = position
        self.key = 0.0

    def draw(self, position:Tuple[int,int]):
        '''
        Draws the effect.
        '''
        pg.draw.circle(
            screen,
            (200,200,200),
            position,
            int(self.key*10),
            int(max(1,self.inverse_key*10))
        )
        
    def update(self):
        '''
        Updates the effect.
        '''
        self.key += td*4
        self.inverse_key = 1-self.key

        if self.key >= 1.0:
            self.deletable = True


class OngoingDI:
    def __init__(self, position: Tuple[float, float]):
        '''
        A counter that is used to represent
        how much damage player dealt in a certain
        area around the counter.
        '''
        self.position: Tuple[float, float] = position
        self.amount: int = 0
        self.update_rect()
        self.lifetime: float = 0.7
        self.deletable: bool = False
        self.glow: float = 1.0

    def update_rect(self):
        '''
        Updates the rect of the indicator.
        
        When the enemy is hit inside of this rect,
        the counter increases.
        '''
        self.rect: pg.Rect = pg.Rect((0,0),(3,2))
        self.rect.center = self.position

    def add(self, amount):
        '''
        Increases the value on the
        counter.
        '''
        self.amount += amount
        self.lifetime = 0.7
        self.glow = 1.0
        self.string = shorten(self.amount)

    def draw(self, position: Tuple[int,int]):
        '''
        Draws the counter.
        '''
        # text
        draw.text(
            self.string,
            position, size=11,
            style='big',
            h=0.5, v=0.5,
            shadows=[(0,-1)]
        )
        # glow
        if int(self.glow*255) > 0:
            draw.image(
                'glow.png',
                position, (40,20),
                h=0.5, v=0.5,
                opacity=int(self.glow*255)
            )

    def update(self):
        '''
        Updates the counter.
        '''
        self.lifetime -= td
        self.glow = lerp(self.glow, 0, td*12)
        if self.lifetime <= 0:
            self.deletable = True


class DamageIndicator(Effect):
    def __init__(self, string:str, position:Tuple[float,float]):
        '''
        When `OngoingDI` gets despawned, at its place
        the `DamageIndicator` gets spawned. It's also a
        counter that shows how much damage player dealt
        in a certain area, but this counter fades out over
        time and doesn't increment when hit.
        '''
        super().__init__()
        self.string: str = string
        self.lifetime: float = 1.0
        self.initial_lifetime: float = 1.0
        self.position: Tuple[float, float] = position
        self.velocity: Tuple[float, float] = [
            random.random()*1-0.5,
            random.random()-5
        ]

    def draw(self, position:Tuple[int,int]):
        '''
        Draws the counter.
        '''
        draw.text(
            self.string,
            position, size=11,
            style='big',
            h=0.5,v=0.5,
            opacity=self.lifetime/self.initial_lifetime*255
        )

    def update(self):
        '''
        Updates the counter.
        '''
        self.lifetime -= td
        if self.lifetime <= 0:
            self.deletable = True
            return
        
        self.position[0] += self.velocity[0]*td*2
        self.position[1] += self.velocity[1]*td

        self.velocity[1] += td*9


class KillIndicator(Effect):
    def __init__(self, amount:int, position:Tuple[float,float]):
        '''
        This counter shows the amount of money
        the player earned when the enemy is killed.
        '''
        super().__init__()
        self.amount: int = amount
        self.smooth: int = 0
        self.smooth_key: float = 0.0
        self.update_counter()

        self.lifetime: float = 2.0
        self.initial_lifetime: float = 2.0
        self.position: Tuple[float, float] = position
        self.velocity: float = 2

        self.glow1_key = 1.0
        self.glow2_key = 1.0

    def update_counter(self):
        '''
        Updates the text on the counter.
        '''
        if self.smooth_key < 1:
            self.smooth_key += td*3
            if self.smooth_key > 1:
                self.smooth_key = 1

            self.smooth = int(self.amount*self.smooth_key)
            self.string = '+'+shorten(self.smooth)+'$'

    def draw(self, position:Tuple[int,int]):
        '''
        Draws the counter.
        '''
        # text
        draw.text(
            self.string,
            position, size=16,
            style='round', color=(180,255,150),
            h=0.5,v=0.5,
            opacity=min(1, self.lifetime/self.initial_lifetime*2.5)*255,
            shadows=[(0,-2)], shadow_color=(20,50,10)
        )
        # glow 1
        draw.image(
            'glow.png',
            position,
            (70,60),
            h=0.5,v=0.5,
            opacity=int(self.glow1_key*255)
        )
        # glow 2
        draw.image(
            'glow.png',
            position,
            (120,5),
            h=0.5,v=0.5,
            opacity=int(self.glow2_key*255)
        )

    def update(self):
        '''
        Updates the object,
        '''
        self.lifetime -= td
        if self.lifetime <= 0:
            self.deletable = True
            return
        
        self.update_counter()
        
        self.position[1] -= td*(self.velocity+1)
        if self.velocity > 0:
            self.velocity -= td*5
            if self.velocity < 0:
                self.velocity = 0

        self.glow1_key = lerp(self.glow1_key, 0, td*7)
        self.glow2_key = lerp(self.glow2_key, 0, td*4)


class SpawnEffect(Effect):
    def __init__(self, position:Tuple[int,int]):
        '''
        An effect that gets played when the enemy spawns.
        '''
        super().__init__()
        self.position: Tuple[int,int] = [position[0]+0.5, position[1]+0.5] # current position
        self.anim1: float = 1.0
        self.anim2: float = 0.0
        self.anim1_smooth: float = 1.0
        self.anim2_smooth: float = 0.0
        self.deletable: bool = False

    def draw(self, position:Tuple[int,int]):
        '''
        Draws the effect.
        '''
        # animation 1
        if self.anim1 > 0.0:
            draw.image(
                'glow.png', position,
                [self.anim1_smooth*128+16]*2, 
                h=0.5,v=0.5, opacity=int((1-self.anim1)*255)
            )
        if self.anim2 > 0.0:
            draw.image(
                'glow.png', position,
                [self.anim2_smooth*48]*2, 
                h=0.5,v=0.5, opacity=int((1-self.anim2)*255)
            )
            draw.image(
                'glow.png', position,
                [self.anim2_smooth*80, 5], 
                h=0.5,v=0.5, opacity=int((1-self.anim2)*255)
            )
            draw.image(
                'glow.png', position,
                [5, self.anim2_smooth*80], 
                h=0.5,v=0.5, opacity=int((1-self.anim2)*255)
            )

    def update(self):
        '''
        Updates the effect.
        '''
        if self.anim1 > 0.0:
            self.anim1 -= td*1
            self.anim1_smooth = easing.QuarticEaseIn(0,1,1).ease(self.anim1)

        if self.anim1 < 0.5:
            self.anim2 += td
            self.anim2_smooth = easing.QuarticEaseOut(0,1,1).ease(self.anim2)

            if self.anim2 > 1.0:
                self.deletable = True


class Enemy:
    def __init__(self, enemy:EnemyData, position:Tuple[int,int]):
        '''
        Guess what? An enemy.
        '''
        self.enemy: EnemyData = enemy # enemy data
        self.position: Tuple[int,int] = [position[0]+0.5, position[1]+0.5] # current position
        self.size: Tuple[float,float] = (
            self.enemy.size[0]/TILE_SIZE,
            self.enemy.size[1]/TILE_SIZE
        ) # size of enemy rect in units
        self.update_rect()

        self.health: int = enemy.health # how much health is left
        self.direction_angle: float = 0.0 # direction the enemy is facing in radians
        self.glow_key: float = 0.0 # how bright the enemy is; used when
                                   # the enemy is hit by a projectile
        self.hp_num_vis: float = 3.0 # the opacity of the number on the health bar
        self.health_bar_color: Tuple[int,int,int] = (80,230,50) # the color of the health bar

        self.shoot_timeout: float = enemy.weapon_speed+(random.random()*2+1)
        self.stun: float = 1 # when greater than 0 the enemy does not move

    def hit(self, damage:int):
        '''
        This function gets called when the
        enemy is hit by a projectile.
        '''
        self.health -= damage
        self.glow_key = 1.0
        self.hp_num_vis = 2.0

    def update_path(self, player_pos:Tuple[float,float], enemies:List):
        '''
        Updates the direction angle of self
        in place according to the provided data.
        '''
        self.direction_angle = points_to_angle(self.position,player_pos)
        # keeping the enemies at a certain distance
        # from each other so they don't form a big blob
        if self.stun <= 0 and len(enemies) != 0:
            for i in enemies:
                if (i.position != self.position) and i.dst_rect.colliderect(self.dst_rect):
                    distance = get_distance(self.position, i.position)
                    angle = points_to_angle(self.position, i.position)
                    self.position[0] -= np.cos(angle)*(1/distance)*0.0003*self.enemy.speed
                    self.position[1] -= np.sin(angle)*(1/distance)*0.0003*self.enemy.speed

    def update_rect(self):
        '''
        Updates the enemy rect in place.
        '''
        self.rect = pg.FRect((0,0), self.size)
        self.rect.center = self.position
        # dst_rect is used to calculate the proximity
        # when to "pull away" enemies from each other
        self.dst_rect = pg.FRect((0,0), (self.size[0]*3,self.size[1]*3))
        self.dst_rect.center = self.position

    def draw(self, position: Tuple[int,int]):
        '''
        Draws the enemy at the desired
        position.
        '''
        # image
        opacity = 255
        if self.stun > 0:
            opacity = (1-self.stun)*255
        draw.image(
            self.enemy.image,
            position,
            self.enemy.size,
            h=0.5, v=0.5,
            opacity=opacity
        )
        # hp bar
        bar_rect = pg.Rect(
            (position[0]-20,position[1]-self.enemy.size[1]/2-7),
            (40,5)
        )
        pg.draw.rect(screen, (30,30,30), bar_rect, 0, 2)
        hp_rect = pg.Rect(
            (position[0]-19,position[1]-self.enemy.size[1]/2-6),

            (38*(self.health/self.enemy.health),3)
        )
        pg.draw.rect(screen, self.health_bar_color, hp_rect, 0, 2)

        if self.hp_num_vis >= 0:
            # text
            draw.text(
                str(self.health),
                (bar_rect.center[0], bar_rect.center[1]+1),
                h=0.5, v=0.5,
                opacity=int(min(255,self.hp_num_vis*400)),
                shadows=[(1,0),(1,1),(0,1)]
            )
        # glow
        if self.glow_key > 0.0 and self.stun <= 0:
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
                
        # some debug things
        if debug_opened:
            rect = pg.Rect((0,0), self.enemy.size)
            rect.center = position
            dst_rect = pg.Rect((0,0), (self.enemy.size[0]*3, self.enemy.size[1]*3))
            dst_rect.center = position
             
            pg.draw.rect(screen, (255,0,0), dst_rect, 1)
            pg.draw.rect(screen, (0,255,0), rect, 1)

    def update(self):
        '''
        Updates the enemy.
        '''
        # moving
        if self.stun <= 0:
            self.position[0] += np.cos(self.direction_angle)*self.enemy.speed*td
            self.position[1] += np.sin(self.direction_angle)*self.enemy.speed*td
        else:
            self.stun -= td

        # glowing
        if self.glow_key > 0:
            self.glow_key -= td*7

        # some hp bar stuff
        if (self.health/self.enemy.health) < 0.3:
            self.hp_num_vis = 1
            self.health_bar_color = (255,50,50)
        elif self.hp_num_vis > 0:
            self.hp_num_vis -= td

        # shooting timer
        if self.shoot_timeout > 0:
            self.shoot_timeout -= td

        # other
        self.update_rect()


class BarDamage:
    def __init__(self, percentage:float):
        '''
        That little red thing that fades out
        on the HP bar when the player gets hit.
        '''
        self.percentage: float = percentage # the right edge's "position" on the screen
                                            # with 0.0 being the leftmost side of the hp
                                            # bar (6px) and 1.0 being the rightmost side (104px) 
        self.lifetime: float = 1.0 # opacity of the color
        self.deletable: bool = False

    def draw(self):
        '''
        Draws the thing
        '''
        # bar
        bar_rect = pg.Rect(6,6,98*self.percentage,4)
        pg.draw.rect(
            screen,
            ((220*self.lifetime)+30,30,30),
            bar_rect,
            0, 2
        )

    def update(self):
        '''
        Updates the thing
        '''
        self.lifetime -= td/1.5
        if self.lifetime <= 0:
            self.deletable = True


class HPDisplay:
    def __init__(self, limit:int):
        '''
        Player's HP bar at the top of the screen.
        '''
        self.limit: int = limit
        self.hp: int = limit
        self.smooth: int = limit
        self.damage_indicators: List[BarDamage] = []
        self.tint_opacity: float = 0.0
        self.glow: float = 0.0
        self.rect: pg.Rect = pg.Rect(5,5,100,7)

    def update_hp(self, change:int):
        '''
        This function is called when the player's
        HP changes.

        `change` argument is how much it changed with
        negative values being "hit" and positive
        being "healed"
        '''
        # change hp
        hp = int(self.hp) # hp before change
        self.hp += change
        self.glow = 1.0

        if self.hp < 0:
            change -= self.hp
            self.hp = 0
        if self.hp > self.limit:
            change -= self.hp-self.limit
            self.hp = self.limit

        # animations
        if change < 0:
            self.tint_opacity = 1.0
            self.damage_indicators.append(BarDamage(hp/self.limit))

    def draw(self):
        '''
        Draws the HP bar
        '''
        # bg
        pg.draw.rect(screen, (30,30,30), self.rect, 0, 2)
        # damage indicators
        for i in self.damage_indicators:
            i.draw()
        # bar
        bar_rect = pg.Rect(6,6,98*(self.smooth/self.limit),5)
        pg.draw.rect(screen, (128,128,128), bar_rect, 0, 2)

        # bar glow effect
        if self.glow > 0:
            draw.image(
                'glow.png', (bar_rect.right, bar_rect.centery),
                (20,20), h=0.5, v=0.5, opacity=int(self.glow*255)
            )
            draw.image(
                'glow.png', (bar_rect.right, bar_rect.centery),
                (6,12), h=0.5, v=0.5, opacity=int(self.tint_opacity*255)
            )
            draw.image(
                'glow.png', (bar_rect.right, bar_rect.centery),
                (40,4), h=0.5, v=0.5, opacity=int(self.glow*255)
            )

        # text
        color = (
            255,
            30+(1-self.tint_opacity)*225,
            30+(1-self.tint_opacity)*225
        )
        draw.text(
            str(self.hp),
            (self.rect.centerx, self.rect.centery+1),
            color, h=0.5, v=0.5,
            shadows=[(0,1),(1,0),(1,1)]
        )

    def update(self): 
        '''
        Updates the HP bar
        '''
        # smooth hp bar
        if round(self.smooth, 1) != self.hp:
            self.smooth = lerp(self.smooth, self.hp, td*5)
        elif self.smooth != self.hp:
            self.smooth = self.hp

        # bar damage indicators
        new = []
        for i in self.damage_indicators:
            i.update()
            if not i.deletable:
                new.append(i)
        self.damage_indicators = new

        # tinting hp text
        if self.tint_opacity > 0:
            self.tint_opacity -= td*2
            if self.tint_opacity < 0:
                self.tint_opacity = 0.0

        # bar glow effect
        if round(self.glow, 1) != 0:
            self.glow = lerp(self.glow, 0, td*4)
        elif self.glow != 0: self.glow = 0


class WaveIndicator:
    def __init__(self):
        '''
        Wave bar at the top of the screen.
        '''
        self.bar_str: str = 'Get ready!' # text below the bar
        self.top_str: str = None # text on top of the bar
        self.bar_int: int = 0 # number below the bar (same as int(self.bar))
        self.bar: float = 0 # bar value
        self.bar_max: float = 0 # maximum value
        self.bar_smooth: float = 10 # smoothed value

        self.tint: float = 0.0
        self.flash1: float = 0.0
        self.flash2: float = 0.0
        self.glow: float = 0.0
        self.rect: pg.Rect = pg.Rect(halfx-75,5,150,7) # bar rect

    def set_max(self, value):
        self.bar_max = value
        self.bar = value
        self.bar_int = int(value)
        self.bar_smooth = 0

        self.flash1 = 1.0
        self.flash2 = 1.0
        self.glow = 1.0
        self.tint = 1.0
    
    def count(self, amount, fx=True):
        '''
        Counts down the number at the bottom of the  bar.
        '''
        self.bar -= amount
        self.bar_int = int(self.bar)
        # glow effects
        if fx:
            self.glow = 1.0
            self.tint = 1.0

    def draw(self):
        '''
        Draws the wave counter.
        '''
        # bar bg
        pg.draw.rect(screen, (30,30,30), self.rect, 0, 2)
        
        # bar
        bar_rect = pg.Rect(halfx-74,6,148*(self.bar_smooth/self.bar_max),5)
        color = (
            230+self.tint*10,
            70+self.tint*120,
            70+self.tint*120
        )
        pg.draw.rect(screen, color, bar_rect, 0, 2)

        # bar glow effect
        if self.glow > 0:
            draw.image(
                'glow.png', (bar_rect.right, bar_rect.centery),
                (20,20), h=0.5, v=0.5, opacity=int(self.glow*255)
            )
            draw.image(
                'glow.png', (bar_rect.right, bar_rect.centery),
                (6,12), h=0.5, v=0.5, opacity=int(self.tint*255)
            )
            draw.image(
                'glow.png', (bar_rect.right, bar_rect.centery),
                (40,4), h=0.5, v=0.5, opacity=int(self.glow*255)
            )

        # text on the bar
        if self.top_str != None:
            draw.text(
                self.top_str, (self.rect.centerx, self.rect.centery+1),
                (255,255,255), shadows = [(0,1),(1,0),(1,1)], h=0.5,v=0.5
            )

        # text on the bottom of the bar
        draw.text(
            self.bar_str, (self.rect.left, self.rect.bottom+4),
            (180,180,180), shadows = [(0,1),(1,0),(1,1)]
        )
        draw.text(
            str(self.bar_int), (self.rect.right, self.rect.bottom+4),
            shadows = [(0,1),(1,0),(1,1)], h=1
        )

        # flash effect
        if self.flash2 > 0:
            draw.image(
                'glow.png', self.rect.center,
                (170,30), h=0.5, v=0.5, opacity=int(self.flash1*255)
            )
            draw.image(
                'glow.png', (self.rect.centerx, self.rect.bottom+2),
                (230,50), h=0.5, v=0.5, opacity=int(self.flash1*255)
            )
            draw.image(
                'glow.png', self.rect.center,
                (250,10), h=0.5, v=0.5, opacity=int(self.flash2*255)
            )
            draw.image(
                'glow.png', (self.rect.centerx, self.rect.bottom+7),
                (225,8), h=0.5, v=0.5, opacity=int(self.flash2*128)
            )


    def update(self):
        '''
        Updates the wave counter.
        '''
        # smooth values
        if round(self.bar_smooth, 2) != self.bar:
            self.bar_smooth = lerp(self.bar_smooth, self.bar, td*7)
        elif self.bar_smooth != self.bar:
            self.bar_smooth = self.bar

        # tint
        if self.tint > 0:
            self.tint -= td*2.5
            if self.tint < 0:
                self.tint = 0

        # glow
        if round(self.glow, 1) != 0:
            self.glow = lerp(self.glow, 0, td*4)
        elif self.glow != 0: self.glow = 0

        # flash
        if round(self.flash1, 2) != 0:
            self.flash1 = lerp(self.flash1, 0, td*4)
        elif self.flash1 != 0: self.flash1 = 0

        if round(self.flash2, 2) != 0:
            self.flash2 = lerp(self.flash2, 0, td)
        elif self.flash2 != 0: self.flash2 = 0


class StaminaBar:
    def __init__(self, amount:int):
        '''
        Stamina bar.
        '''
        self.max: int = amount # maximum amount of stamina
        self.current: int = amount # current stamina
        self.key: float = 0 # animation key
        self.glow: float = 0.0 # glow opacity

    def update_value(self, new_value:int):
        '''
        Updates the value on the bar.
        '''
        self.current = new_value
        self.glow = 1.0

    def draw(self, position:Tuple[int,int]):
        '''
        Draws the bar.
        '''
        if self.key <= 0.0:
            return
        
        # position and easing
        ease = easing.QuarticEaseOut(0,1,1).ease(self.key)
        rect = pg.Rect((0,0), [round(ease*60)]*2)
        rect.center = position

        # bg arc
        pg.draw.arc(screen, (40,40,40), rect, -0.61, 0.6, 2)

        # bar
        color = (
            255,
            220+self.glow*25,
            60+self.glow*100
        )
        angle = (self.current/self.max)*1.3-0.6
        pg.draw.arc(screen, color, rect, -0.61, angle)
        # glow
        if self.glow > 0:
            glow_pos = [
                np.cos(angle)*(30*ease)+position[0],
                -np.sin(angle)*(30*ease)+position[1]+1
            ]
            draw.image(
                'glow.png', glow_pos,
                (14,12), h=0.5, v=0.5, 
                opacity=int(max(0,self.glow*128))
            )
            draw.image(
                'glow.png', glow_pos,
                (24,4), h=0.5, v=0.5, 
                opacity=int(self.glow*255)
            )

    def update(self):
        '''
        Updates the bar.
        '''
        # glow
        if round(self.glow, 2) != 0:
            self.glow = lerp(self.glow, 0, td*6)
        elif self.glow != 0:
            self.glow = 0

        # fading animation
        if self.current < self.max:
            if self.key < 1.0:
                self.key += td*4
        elif self.key > 0.0:
            self.key -= td*2

        if self.key > 1.0:
            self.key = 1.0
        if self.key < 0.0:
            self.key = 0.0


class ScoreCounter:
    def __init__(self):
        '''
        Score counter at the top of the screen.
        '''
        self.score: int = 0 # current score
        self.smooth_score: float = 0 # smoothed score
        self.glow1: float = 0.0 # big glow opacity
        self.glow2: float = 0.0 # small glow opacity

    def add(self, amount:int):
        '''
        Adds amount to score counter.
        '''
        self.score += amount
        self.glow1 = 1.0
        self.glow2 = 1.0

    def draw(self):
        '''
        Draws the counter.
        '''
        offset = max(0,self.glow1*6-3)
        # counter
        string = str(round(self.smooth_score))
        draw.text(
            round(self.smooth_score), (windowx-7-offset, 7),
            style='round', size=16, h=1,
            shadows=[(0,-2)]
        )
        # faded out zeroes
        zeroes = max(0,8-len(string))
        if zeroes > 0:
            draw.text(
                '0'*zeroes, (windowx-7-len(string)*9-offset,7),
                style='round', size=16, h=1,
                shadows=[(0,-2)], opacity=80
            )

        # glow
        if self.glow2 > 0:
            draw.image(
                'glow.png', (windowx-40-offset,14), (90,30),
                h=0.5, v=0.5, opacity=int(self.glow1*255)
            )
            draw.image(
                'glow.png', (windowx-40-offset,14), (175,6),
                h=0.5, v=0.5, opacity=int(self.glow2*255)
            )

    def update(self):
        '''
        Updates the counter.
        '''
        # smoothing score counter
        if round(self.smooth_score, 1) != self.score:
            self.smooth_score = lerp(self.smooth_score, self.score, td*7)
        elif self.smooth_score != self.score:
            self.smooth_score = self.score

        # big glow
        if self.glow1 > 0.0:
            self.glow1 -= td*2

        # small glow
        if round(self.glow2, 2) != 0:
            self.glow2 = lerp(self.glow2, 0, td*1.5)
        elif self.glow2 != 0:
            self.glow2 = 0


class BalanceCounter:
    def __init__(self):
        '''
        Balance counter at the top of the screen.
        '''
        self.balance: int = 0 # current balance
        self.smooth_balance: float = 0 # smoothed balance
        self.glow1: float = 0.0 # big glow opacity
        self.glow2: float = 0.0 # small glow opacity

    def add(self, amount:int):
        '''
        Adds amount to balance counter.
        '''
        self.balance += amount
        self.glow1 = 1.0
        self.glow2 = 1.0

    def draw(self):
        '''
        Draws the counter.
        '''
        offset = max(0,self.glow1*6-3)
        # counter
        string = str(round(self.smooth_balance))
        draw.text(
            round(self.smooth_balance), (windowx-7-offset,27),
            style='big', size=11, h=1, color=(170,255,130),
            shadows=[(0,-2)]
        )
        # faded out zeroes
        zeroes = max(0,7-len(string))
        if zeroes > 0:
            draw.text(
                '0'*zeroes, (windowx-7-len(string)*7-offset,27),
                style='big', size=11, h=1, shadows=[(0,-2)],
                opacity=80, color=(230,255,220)
            )
        # dollar sign
        draw.text(
            '$', (windowx-7-max(7,len(string))*7-offset,27),
            style='big', size=11, h=1, color=(170,255,130),
            shadows=[(0,-2)]
        )

        # glow
        if self.glow2 > 0:
            draw.image(
                'glow.png', (windowx-35-offset,32), (80,25),
                h=0.5, v=0.5, opacity=int(self.glow1*255)
            )
            draw.image(
                'glow.png', (windowx-35-offset,32), (160,4),
                h=0.5, v=0.5, opacity=int(self.glow2*255)
            )

    def update(self):
        '''
        Updates the counter.
        '''
        # smoothing balance counter
        if round(self.smooth_balance, 1) != self.balance:
            self.smooth_balance = lerp(self.smooth_balance, self.balance, td*7)
        elif self.smooth_balance != self.balance:
            self.smooth_balance = self.balance

        # big glow
        if self.glow1 > 0.0:
            self.glow1 -= td*2

        # small glow
        if round(self.glow2, 2) != 0:
            self.glow2 = lerp(self.glow2, 0, td*1.5)
        elif self.glow2 != 0:
            self.glow2 = 0
            

class Dungeon:
    def __init__(self, wave:WaveData, map:MapData):
        '''
        The entire gameplay.
        '''
        # map and camers
        self.map: MapData = map # map data

        self.cam_center = map.player_spawn # where the cam is supposed to be
        self.cam_smoothed_center = [ # current cam position
            map.player_spawn[0],
            map.size[1]+10
        ]

        # player
        self.player: PlayerData = datapack.player # player data
        self.player_pos: Tuple[float,float] = map.player_spawn # player position
        self.player_vel: Tuple[float,float] = [0,0] # player velocity
        self.player_health: int = self.player.health # current player health
        self.update_player_rect()

        # stamina
        self.available_stamina: float = self.player.stamina # stamina
        self.stamina_restore_timer: float = 0.0 # how much time is left before the stamina gets restored
        self.stamina_restore_speed: float = 2.0

        # projectiles and weapons
        self.projectiles: List[Projectile] = [] # guess what
        self.weapon: WeaponData = datapack.weapons[0] # current weapon player has
        self.shooting_timer: float = 0.0 # how much time is left before a player can shoot

        # enemies
        self.enemies: List[Enemy] = [] # guess what

        # effects
        self.effects: List[Effect] = [] # list of effects
        self.damage_indicators: List[OngoingDI] = [] # list of damage indicators
        self.shakiness: float = 0.0 # how shaky the screen is
        self.shake_pos: Tuple[float,float] = [0,0] # shake pos offset
        self.dim: float = 0.0 # dim opacity from 0.0 to 1.0
        self.smooth_dim: float = 1.0 # smoothed out `dim`
        self.vignette_opacity: float = 0.0 # red blood vignette opacity
        self.dead_key: float = 0.0 # smoothing out death animation
        self.smooth_dead_key: float = 0.0 # more smoothing out death animation

        # wave data
        self.wave: WaveData = wave # wave data
        self.wave_bar: WaveIndicator = WaveIndicator() # wave bar on top 
        self.wave_bar.set_max(10)
        self.is_intermission: bool = True # guess what
        self.intermission_timer: float = 10 # how much time of intermission is left
        self.wave_number: int = 0 # wave number
        self.waves_before_boss: int = wave.boss_every-1 # how much waves left before boss spawns

        # enemy spawning
        self.enemy_queue: List[EnemyData] = [] # a queue of enemies to spawn
        self.spawn_timer: float = 0 # time before spawning the next enemy
        self.queue_manager: QueueManager = QueueManager(wave) # manages what enemies to spawn
        self.spawn_max: int = random.randint(*wave.limit_start) # max amount of enemies on field

        # ui
        self.health_bar: HPDisplay = HPDisplay(self.player.health) # health bar
        self.stamina_bar: StaminaBar = StaminaBar(self.player.stamina) # stamina bar
        self.score_counter: ScoreCounter = ScoreCounter() # score counter
        self.balance_counter: BalanceCounter = BalanceCounter() # balance counter

        # stats
        self.balance: int = 0 # player balance
        self.score: int = 0 # player score
        self.level: int = 1 # current player money multiplier
        self.kills: int = 0 # amount of enemies player killed
        self.kills_to_next_level: int = 5 # how much kills left to reach the next level

        # other
        self.paused: bool = False # whether to show the pause menu
        self.playing: bool = True # whether to run the game
        self.dead: bool = False # whether the player is dead


    def draw_debug(self):
        '''
        Draws debug info on screen.
        '''
        data = {
            'Enemies':     f'{len(self.enemies)} (IQ: {len(self.enemy_queue)})',
            'Effects':     f'{len(self.effects)} (DI: {len(self.damage_indicators)})',
            'Projectiles': f'{len(self.projectiles)}',
            'Stamina':     f'{round(self.available_stamina, 2)}/{self.player.stamina} ({round(self.stamina_restore_timer, 2)}s to restore)',
        }
        index = 0
        for key in data:
            value = data[key]
            draw.text(key, (50,70+index*10), shadows=[(0,1)])
            draw.text(value, (100,70+index*10), shadows=[(0,1)])
            index += 1


    def get_enemy_projectiles(self) -> List[Projectile]:
        '''Returns the list of all `enemy` type projectiles.'''
        return [i for i in self.projectiles if i.projectile.hit_type == 'enemy']

    def get_player_projectiles(self) -> List[Projectile]:
        '''Returns the list of all `player` type projectiles.'''
        return [i for i in self.projectiles if i.projectile.hit_type == 'player']

    def units_to_px(self, pos: Tuple[float,float]) -> Tuple[float,float]:
        '''
        Converts map coordinates (units) to coordinates on screen (pixels).

        Also applies shaking.
        '''
        return [
            halfx-(self.cam_smoothed_center[0]-pos[0])*TILE_SIZE+self.shake_pos[0],
            halfy-(self.cam_smoothed_center[1]-pos[1])*TILE_SIZE+self.shake_pos[1]
        ]
    
    def get_spawn_location(self):
        '''
        Returns a random enemy spawn location.
        '''
        pos = random.choice(self.map.enemy_spawn_locations)
        return [pos[0], pos[1]] 
    
    def add_balance(self, amount:int):
        '''
        Adds money to player's balance.
        '''
        self.balance += amount
        self.balance_counter.add(amount)

    def add_score(self, amount:int):
        '''
        Adds score to player's score counter.

        Applies score multiplier.
        '''
        amount *= self.level
        self.score += amount
        self.score_counter.add(amount)

    def damage_player(self, amount:int):
        '''Damages the player.'''
        self.player_health -= amount
        self.health_bar.update_hp(-amount)
        self.shakiness += 2
        self.vignette_opacity += 0.5

    def damage_enemy(self, amount:int, position:Tuple[float, float]):
        '''
        This function gets called when the enemy is
        hit.
        '''
        for i in self.damage_indicators:
            if i.rect.collidepoint(position):
                i.add(amount)
                i.position[0] = lerp(i.position[0], position[0], 0.02)
                i.position[1] = lerp(i.position[1], position[1], 0.02)
                i.update_rect()
                return
            
        di = OngoingDI(position)
        di.add(amount)
        self.damage_indicators.append(di)

    def kill_enemy(self, position:Tuple[float,float], cost:int):
        '''
        This function gets called when an enemy is
        killed.
        '''
        self.effects.append(KillIndicator(cost, position))
        self.add_balance(cost)
        self.add_score(cost)
        self.shakiness += 1
        self.wave_bar.count(1)

    def pause(self):
        '''
        Pauses or unpauses the game.
        '''
        if self.dead:
            return
        self.paused = not self.paused
        self.dim = int(self.paused)*0.5
        self.playing = not self.playing

    def kill(self):
        '''
        Kills the player and terminates the game.
        '''
        self.dead = True
        self.playing = False
        self.paused = False
    
    def draw_ui(self):
        '''
        Draws the HUD.
        '''
        # vignette
        if self.vignette_opacity > 0:
            draw.image(
                'vignette.png',
                (0,0), (windowx,windowy),
                opacity=int(self.vignette_opacity*255)
            )

        # health bar
        self.health_bar.draw()
        # wave bar
        self.wave_bar.draw()
        # stamina bar
        self.stamina_bar.draw(self.global_player_pos)
        # score counter
        self.score_counter.draw()
        # balance counter
        self.balance_counter.draw()
        # current weapon
        draw.image(
            self.weapon.image, (windowx-10, windowy-10),
            self.weapon.size, h=1, v=1
        )
        draw.text(
            self.weapon.name, (windowx-17-self.weapon.size[0],windowy-10),
            h=1, v=1, shadows=[(0,-1)]
        )

    def draw_player(self):
        '''
        Draws the player.
        '''
        # pointer bar
        draw.image(
            'cursor_bar.png',
            self.global_player_pos,
            (1,150*(1-self.shooting_timer/self.weapon.speed)),
            h=0.5,v=0.5,
            rotation=self.mouse_degrees_angle
        )

        # player
        draw.image(
            self.player.anim.image,
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

    def update_player_rect(self):
        '''
        Updates player rect.
        '''
        self.player_rect = pg.FRect((0,0),(1,1))
        self.player_rect.center = self.player_pos

    def update_player(self):
        '''
        Updates the player.
        '''
        initial_pos = [self.player_pos[0], self.player_pos[1]]
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

            self.update_player_rect()

        # making the player not go outside the map
        self.player_pos[0] = max(0.5, min(self.map.size[0]-0.5, self.player_pos[0]))
        self.player_pos[1] = max(0.5, min(self.map.size[1]-0.5, self.player_pos[1])) 
        
        # decreasing stamina when sprinting
        if initial_pos != self.player_pos and\
            keys[pg.K_LSHIFT] and moving and self.available_stamina > 0:
                self.available_stamina -= td
                self.stamina_bar.update_value(self.available_stamina)
                self.stamina_restore_timer = self.stamina_restore_speed
        # resting to restore stamina
        elif self.stamina_restore_timer > 0:
            self.stamina_restore_timer -= td
        # restoring stamina when rested
        elif self.available_stamina < self.player.stamina:
            self.available_stamina += td*2
            self.stamina_bar.update_value(self.available_stamina)

        # updating animation
        self.player.anim.set_animation(
            'walk' if initial_pos != self.player_pos else 'stand'
        )
        self.player.anim.update()

        # killing player
        if self.player_health <= 0:
            self.kill()


    def update_wave(self):
        # the bar on top
        self.wave_bar.update()

        # intermission
        if self.is_intermission:
            self.intermission_timer -= td
            self.wave_bar.count(td, fx=False)

            # switching to gameplay
            if self.intermission_timer <= 0 or pg.K_SPACE in keysdown:
                self.wave_number += 1
                self.queue_manager.step()
                # boss wave
                if self.waves_before_boss <= 0:
                    self.waves_before_boss = self.wave.boss_every
                    self.enemy_queue = [self.wave.random_boss()]
                # normal wave
                else:
                    self.enemy_queue = self.queue_manager.gen_queue()

                self.wave_bar.set_max(len(self.enemy_queue))
                self.wave_bar.bar_str = 'Enemies remaining'
                self.wave_bar.top_str = f'Wave {self.wave_number}'

                self.is_intermission = False
                self.spawn_max += random.randint(*self.wave.limit_increase)
                if self.spawn_max > self.wave.limit_end:
                    self.spawn_max = self.wave.limit_end

        # wave
        else:
            # spawning enemies
            if len(self.enemies) < self.spawn_max:
                self.spawn_timer -= td

            if len(self.enemy_queue) > 0 and self.spawn_timer <= 0 and len(self.enemies) < self.spawn_max:
                self.spawn_timer = random.randint(*self.wave.spawn_delay)
                position = self.get_spawn_location()
                self.enemies.append(Enemy(self.enemy_queue[0], position))
                self.effects.append(SpawnEffect(position))
                self.enemy_queue.pop(0)

            # switching to intermission
            if len(self.enemy_queue) == 0 and len(self.enemies) == 0:
                self.is_intermission = True
                self.wave_bar.set_max(10)
                self.waves_before_boss -= 1
                self.intermission_timer = 10
                self.wave_bar.bar_str = 'Intermission'
                # boss message
                if self.waves_before_boss <= 0:
                    self.wave_bar.top_str = f'Wave {self.wave_number+1} - Boss incoming!'
                # normal message
                else:
                    self.wave_bar.top_str = f'SPACE to skip to Wave {self.wave_number+1}'


    def draw(self):
        '''
        Draws everything.
        '''
        # map
        draw.image(
            self.map.image,
            self.units_to_px((0,0)),
            self.map.pixel_size
        )

        # projectiles
        for i in self.projectiles:
            i.draw(self.units_to_px(i.position))

        # enemies
        for i in self.enemies:
            i.draw(self.units_to_px(i.position))

        # effects
        for i in self.effects:
            i.draw(self.units_to_px(i.position))

        # damage indicators
        for i in self.damage_indicators:
            i.draw(self.units_to_px(i.position))

        # player
        self.draw_player()
        
        # ui
        self.draw_ui()

        # some debug things
        if debug_opened:
            pos = self.units_to_px(self.player_rect.topleft)
            pg.draw.rect(screen, (0,0,255), pg.FRect(pos, (TILE_SIZE,TILE_SIZE)), 1)

        # death gui
        if self.dead:
            # red overlay
            draw.image(
                'red.png', size=(windowx,windowy),
                opacity=int(200-self.smooth_dead_key*120)
            )
            # text
            draw.image(
                'dead.png', (halfx, halfy), opacity=int(155+self.smooth_dead_key*100),
                size=(330-self.smooth_dead_key*60,110-self.smooth_dead_key*20), h=0.5, v=0.5
            )
            
        # dimming screen
        if self.smooth_dim != 0:
            draw.image(
                'black.png', size=(windowx,windowy),
                opacity=int(self.smooth_dim*255)
            )

        # some debug info
        if debug_opened:
            self.draw_debug()

        # mouse crosshair
        draw.image(
            'crosshair.png',
            mouse_pos,
            (11,11),
            h=0.5,v=0.5,
        )


    def update(self):
        '''
        Updates the game.
        '''
        # dimming screen
        if round(self.smooth_dim, 3) == self.dim:
            self.smooth_dim = self.dim
        else:
            self.smooth_dim = lerp(self.smooth_dim, self.dim, td*6)
            
        # death animation
        if self.dead:
            if self.dead_key < 1.0:
                self.dead_key += td/1.5
                self.smooth_dead_key = easing.ExponentialEaseOut(0,1,1).ease(self.dead_key)
                if self.dead_key > 1.0:
                    self.dead_key = 1.0

        # pausing and pause menu
        if pg.K_ESCAPE in keysdown:
            self.pause()
        
        if not self.playing:
            return

        # updating cursor
        self.global_player_pos = self.units_to_px(self.player_pos)
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

        # waves
        self.update_wave()

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
                if self.weapon.recoil != 0:
                    relative = [np.cos(self.mouse_angle),np.sin(self.mouse_angle)]
                    self.player_pos[0] -= relative[0]*self.weapon.recoil
                    self.player_pos[1] -= relative[1]*self.weapon.recoil
                    self.update_player_rect()

        # updating player
        self.update_player()

        # updating stamina
        self.stamina_bar.update()

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
                        self.damage_enemy(i.damage, i.position)
                
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
                cost = i.enemy.random_cost()
                self.kill_enemy(i.position, cost)
                continue

            # shooting
            if i.shoot_timeout <= 0:
                while i.shoot_timeout < 0:
                    i.shoot_timeout += i.enemy.weapon_speed
                    i.glow_key = 0.3
                    for j in range(i.enemy.amount):
                        self.projectiles.append(Projectile(
                            i.enemy.projectile,
                            [i.position[0], i.position[1]],
                            i.direction_angle+i.enemy.random_range()
                        ))

            # updating
            i.update_path(self.player_pos, [j for j in self.enemies if j.position != i.position])
            i.update()
            new.append(i)

        self.enemies = new

        # damage indicators
        new = []
        for i in self.damage_indicators:
            i.update()
            if not i.deletable:
                new.append(i)
            else:
                self.effects.append(DamageIndicator(i.string, i.position))
        self.damage_indicators = new
        
        # effects
        new = []
        for i in self.effects:
            i.update()
            if not i.deletable:
                new.append(i)
        self.effects = new

        # health bar
        self.health_bar.update()

        # score counter
        self.score_counter.update()
        
        # balance counter
        self.balance_counter.update()

        # vignette
        if self.vignette_opacity > 1.0:
            self.vignette_opacity = 1.0
        if self.vignette_opacity > 0:
            self.vignette_opacity -= td*2
            if self.vignette_opacity < 0:
                self.vignette_opacity = 0



# app variables
                
maps = [
    MapData({
        "image":        "maps/map1.png",
        "size":         [20,10],
        "spawn":        [10,5],
        "enemy_spawns": [[1,8], [18,1], [18,8], [1,1]]
    })
]


datapacks: Dict[str, Datapack]
datapack: Datapack
refresh_datapacks()

app = Dungeon(
    datapack.waves[0],
    maps[0]
)
debug_opened = False
fps_graph = []


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
                fps_graph = []

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
    prev_dfps = float(dfps)
    dfps = round(clock.get_fps(), 2) # getting fps
    td = time.time()-start_td # calculating timedelta for the next frame