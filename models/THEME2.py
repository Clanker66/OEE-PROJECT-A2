"""
╔══════════════════════════════════════════════════════════════════════╗
║          PROJECT ABSOLUTE LIGHT  ·  Laser Puzzle Engine v2          ║
║          Architecture: State Machine · Physics · Particle FX        ║
╚══════════════════════════════════════════════════════════════════════╝

STRUCTURE:
  VecMath          – Pure math helpers (no state)
  PhysicsEngine    – Stateless ray tracer
  ParticleSystem   – Sparks, glows, fx
  Mirror           – Rotatable reflector
  Blocker          – Opaque wall segment
  Splitter         – Splits laser into two beams
  MovingObstacle   – Oscillating blocker
  Sensor           – Target receiver
  Level            – World state + level data
  Renderer         – All drawing, layered
  UI               – Panels, buttons, transitions
  States           – Menu / Playing / LevelComplete / GameOver
  Game             – Root driver
"""

import pygame
import math
import sys
import random
import time

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# ═══════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════
W, H = 1100, 720
FPS  = 60

# Palette
C = {
    "bg":           (6,  8,  20),
    "room_bg":      (10, 14, 35),
    "room_border":  (25, 40, 90),
    "laser":        (255, 55, 55),
    "laser2":       (55, 200, 255),   # splitter beam
    "mirror":       (140, 210, 255),
    "mirror_sel":   (255, 215, 70),
    "mirror_hover": (180, 240, 180),
    "blocker":      (80,  90, 130),
    "splitter":     (200, 100, 255),
    "mover":        (70, 180, 140),
    "sensor_on":    (0,  255, 120),
    "sensor_off":   (220, 60,  60),
    "sensor_armed": (255, 200, 30),
    "text":         (210, 220, 255),
    "text_dim":     (100, 110, 160),
    "panel":        (12, 18, 45),
    "panel_border": (30, 50, 120),
    "gold":         (255, 215, 70),
    "red":          (255, 60, 60),
    "green":        (60, 255, 140),
    "white":        (240, 245, 255),
}

ROOM = pygame.Rect(320, 60, 660, 600)
MAX_BOUNCES = 12
MIRROR_HALF = 55
SENSOR_R    = 16
TOLERANCE   = 22

# ═══════════════════════════════════════════════════════════════════════
# VEC MATH  (pure, no state)
# ═══════════════════════════════════════════════════════════════════════
class V:
    @staticmethod
    def norm(vx, vy):
        m = math.hypot(vx, vy)
        return (vx/m, vy/m) if m > 1e-12 else (0.0, 0.0)

    @staticmethod
    def reflect(dx, dy, nx, ny):
        dot = dx*nx + dy*ny
        return V.norm(dx - 2*dot*nx, dy - 2*dot*ny)

    @staticmethod
    def ray_seg(ox, oy, dx, dy, x1, y1, x2, y2):
        """Returns (t, px, py) or None"""
        sx, sy = x2-x1, y2-y1
        D = dx*sy - dy*sx
        if abs(D) < 1e-9: return None
        t = ((x1-ox)*sy - (y1-oy)*sx) / D
        u = ((x1-ox)*dy - (y1-oy)*dx) / D
        if t > 0.5 and 0.0 <= u <= 1.0:
            return t, ox + t*dx, oy + t*dy
        return None

    @staticmethod
    def lerp(a, b, t):
        return a + (b-a) * t

    @staticmethod
    def dist(x1, y1, x2, y2):
        return math.hypot(x2-x1, y2-y1)

# ═══════════════════════════════════════════════════════════════════════
# PARTICLE SYSTEM
# ═══════════════════════════════════════════════════════════════════════
class Particle:
    __slots__ = ['x','y','vx','vy','life','max_life','r','color','type']
    def __init__(self, x, y, vx, vy, life, r, color, kind='spark'):
        self.x, self.y = x, y
        self.vx, self.vy = vx, vy
        self.life = self.max_life = life
        self.r = r
        self.color = color
        self.type = kind

class ParticleSystem:
    def __init__(self):
        self.particles = []

    def spark(self, x, y, color, count=8):
        for _ in range(count):
            a = random.uniform(0, math.pi*2)
            spd = random.uniform(1.5, 5.0)
            self.particles.append(Particle(
                x, y,
                math.cos(a)*spd, math.sin(a)*spd,
                random.uniform(20, 45),
                random.uniform(1.5, 3.5),
                color, 'spark'
            ))

    def glow_burst(self, x, y, color, count=20):
        for _ in range(count):
            a = random.uniform(0, math.pi*2)
            spd = random.uniform(0.5, 3.0)
            self.particles.append(Particle(
                x, y,
                math.cos(a)*spd, math.sin(a)*spd,
                random.uniform(40, 80),
                random.uniform(3, 8),
                color, 'glow'
            ))

    def ambient(self, x, y, color):
        """Continuous small ambient particles"""
        self.particles.append(Particle(
            x + random.uniform(-5,5),
            y + random.uniform(-5,5),
            random.uniform(-0.3, 0.3),
            random.uniform(-1.2, -0.3),
            random.uniform(60, 120),
            random.uniform(1, 2.5),
            color, 'ambient'
        ))

    def update(self):
        alive = []
        for p in self.particles:
            p.life -= 1
            if p.life <= 0: continue
            p.x += p.vx
            p.y += p.vy
            p.vy += 0.05 if p.type == 'spark' else 0.01
            p.vx *= 0.97
            alive.append(p)
        self.particles = alive

    def draw(self, surf):
        for p in self.particles:
            alpha = p.life / p.max_life
            r = max(1, int(p.r * alpha))
            a = int(255 * alpha)
            color = (*p.color[:3], a)
            s = pygame.Surface((r*2+2, r*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, color, (r+1, r+1), r)
            surf.blit(s, (int(p.x)-r-1, int(p.y)-r-1))

# ═══════════════════════════════════════════════════════════════════════
# GAME OBJECTS
# ═══════════════════════════════════════════════════════════════════════
class Mirror:
    def __init__(self, x, y, angle, min_a=-180, max_a=180, label=""):
        self.x, self.y = float(x), float(y)
        self.angle = float(angle)
        self.min_a, self.max_a = min_a, max_a
        self.label = label
        self.selected = False
        self.hovered = False
        self._sparks_pending = False

    def endpoints(self):
        r = math.radians(self.angle)
        dx = math.cos(r) * MIRROR_HALF
        dy = math.sin(r) * MIRROR_HALF
        return (self.x-dx, self.y-dy), (self.x+dx, self.y+dy)

    def normal(self):
        r = math.radians(self.angle + 90)
        return math.cos(r), math.sin(r)

    def rotate(self, delta):
        new = self.angle + delta
        self.angle = max(self.min_a, min(self.max_a, new))

    def at_limit(self):
        return self.angle <= self.min_a + 0.5 or self.angle >= self.max_a - 0.5

    def draw(self, surf, font_sm):
        p1, p2 = self.endpoints()
        if self.selected:
            color = C["mirror_sel"]
            w = 5
            # Selection glow
            for gw in [14, 9]:
                gc = (*C["mirror_sel"], 40)
                gs = pygame.Surface((W, H), pygame.SRCALPHA)
                pygame.draw.line(gs, gc, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), gw)
                surf.blit(gs, (0,0))
        elif self.hovered:
            color = C["mirror_hover"]
            w = 4
        else:
            color = C["mirror"]
            w = 3

        pygame.draw.line(surf, color, (int(p1[0]), int(p1[1])), (int(p2[0]), int(p2[1])), w)

        # Center dot
        cdot = C["mirror_sel"] if self.selected else (80, 140, 200)
        pygame.draw.circle(surf, cdot, (int(self.x), int(self.y)), 5)

        # Angle arc indicator when selected
        if self.selected:
            span = self.max_a - self.min_a
            if span < 360:
                # Draw arc showing constraint
                arc_r = pygame.Rect(int(self.x)-20, int(self.y)-20, 40, 40)
                try:
                    sa = math.radians(-self.max_a)
                    ea = math.radians(-self.min_a)
                    pygame.draw.arc(surf, (*C["mirror_sel"], 100), arc_r, sa, ea, 1)
                except: pass

        # Label
        if self.label:
            lbl = font_sm.render(self.label, True, C["text_dim"])
            surf.blit(lbl, (int(self.x)+8, int(self.y)-20))


class Blocker:
    """Opaque obstacle that blocks the laser"""
    def __init__(self, x1, y1, x2, y2):
        self.x1, self.y1 = x1, y1
        self.x2, self.y2 = x2, y2

    def draw(self, surf):
        pygame.draw.line(surf, C["blocker"],
                         (int(self.x1), int(self.y1)),
                         (int(self.x2), int(self.y2)), 7)
        # glow
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.line(gs, (*C["blocker"], 60),
                         (int(self.x1), int(self.y1)),
                         (int(self.x2), int(self.y2)), 16)
        surf.blit(gs, (0,0))


class Splitter:
    """Splits beam into reflected + transmitted"""
    def __init__(self, x, y, angle, min_a=-180, max_a=180):
        self.x, self.y = float(x), float(y)
        self.angle = float(angle)
        self.min_a, self.max_a = min_a, max_a
        self.selected = False
        self.hovered = False

    def endpoints(self):
        r = math.radians(self.angle)
        dx = math.cos(r) * MIRROR_HALF
        dy = math.sin(r) * MIRROR_HALF
        return (self.x-dx, self.y-dy), (self.x+dx, self.y+dy)

    def normal(self):
        r = math.radians(self.angle + 90)
        return math.cos(r), math.sin(r)

    def rotate(self, delta):
        self.angle = max(self.min_a, min(self.max_a, self.angle + delta))

    def draw(self, surf, font_sm):
        p1, p2 = self.endpoints()
        color = C["mirror_sel"] if self.selected else C["splitter"]
        w = 5 if self.selected else 3

        # Dashed line to indicate partial transparency
        px1, py1 = int(p1[0]), int(p1[1])
        px2, py2 = int(p2[0]), int(p2[1])
        length = math.hypot(px2-px1, py2-py1)
        if length > 0:
            dash = 10
            gap  = 5
            steps = int(length / (dash + gap))
            for i in range(steps + 1):
                t0 = i * (dash + gap) / length
                t1 = min(1.0, t0 + dash / length)
                sx = int(px1 + (px2-px1)*t0)
                sy = int(py1 + (py2-py1)*t0)
                ex = int(px1 + (px2-px1)*t1)
                ey = int(py1 + (py2-py1)*t1)
                pygame.draw.line(surf, color, (sx, sy), (ex, ey), w)

        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), 5)

        lbl = font_sm.render("SPLIT", True, (*C["splitter"], 180))
        surf.blit(lbl, (int(self.x)+8, int(self.y)-20))


class MovingObstacle:
    """Oscillates between two points"""
    def __init__(self, x1, y1, x2, y2, speed=0.008, ox_len=80):
        self.ax, self.ay = x1, y1
        self.bx, self.by = x2, y2
        self.speed = speed
        self.t = random.uniform(0, math.pi*2)
        self.ox_len = ox_len  # half-length of the obstacle

    def update(self):
        self.t += self.speed

    @property
    def pos(self):
        tt = (math.sin(self.t) + 1) / 2
        return V.lerp(self.ax, self.bx, tt), V.lerp(self.ay, self.by, tt)

    def endpoints(self):
        mx, my = self.pos
        r = math.radians(90)
        dx = math.cos(r) * self.ox_len
        dy = math.sin(r) * self.ox_len
        return (mx-dx, my-dy), (mx+dx, my+dy)

    def draw(self, surf):
        p1, p2 = self.endpoints()
        # Path indicator
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.line(gs, (*C["mover"], 20),
                         (int(self.ax), int(self.ay)),
                         (int(self.bx), int(self.by)), 2)
        surf.blit(gs, (0,0))

        pygame.draw.line(surf, C["mover"],
                         (int(p1[0]), int(p1[1])),
                         (int(p2[0]), int(p2[1])), 7)
        pygame.draw.circle(surf, C["mover"], (int(self.pos[0]), int(self.pos[1])), 5)


class Sensor:
    def __init__(self, x, y, label="TARGET"):
        self.x, self.y = x, y
        self.label = label
        self.active = False
        self.pulse_t = 0.0
        self.hit_flash = 0

    def update(self, dt):
        self.pulse_t += dt * 3.0
        if self.hit_flash > 0:
            self.hit_flash -= dt * 60

    def draw(self, surf, font_sm):
        color = C["sensor_on"] if self.active else C["sensor_off"]
        pulse = math.sin(self.pulse_t) * 5

        # Outer glow
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        glow_r = int(SENSOR_R + 20 + pulse)
        glow_a = 80 if self.active else 30
        pygame.draw.circle(gs, (*color, glow_a), (int(self.x), int(self.y)), glow_r)
        surf.blit(gs, (0,0))

        # Ring
        ring_r = SENSOR_R + int(pulse)
        pygame.draw.circle(surf, color, (int(self.x), int(self.y)), ring_r, 2)

        # Fill
        inner_color = [min(255, c + 40 if self.active else c) for c in color]
        pygame.draw.circle(surf, inner_color[:3], (int(self.x), int(self.y)), SENSOR_R - 3)

        # Cross-hair
        cl = SENSOR_R - 4
        pygame.draw.line(surf, (*color, 150), (int(self.x)-cl, int(self.y)), (int(self.x)+cl, int(self.y)), 1)
        pygame.draw.line(surf, (*color, 150), (int(self.x), int(self.y)-cl), (int(self.x), int(self.y)+cl), 1)

        # Label
        lbl = font_sm.render(self.label, True, color)
        surf.blit(lbl, (int(self.x) - lbl.get_width()//2, int(self.y) + SENSOR_R + 4))

        # Hit flash
        if self.hit_flash > 0:
            fa = int(min(255, self.hit_flash * 4))
            fs = pygame.Surface((W, H), pygame.SRCALPHA)
            pygame.draw.circle(fs, (*C["sensor_on"], fa), (int(self.x), int(self.y)), SENSOR_R + 30)
            surf.blit(fs, (0,0))

# ═══════════════════════════════════════════════════════════════════════
# PHYSICS ENGINE (stateless)
# ═══════════════════════════════════════════════════════════════════════
class PhysicsEngine:

    @staticmethod
    def room_walls():
        """Returns wall segments as (x1,y1,x2,y2) list"""
        r = ROOM
        return [
            (r.left, r.top, r.right, r.top),
            (r.right, r.top, r.right, r.bottom),
            (r.left, r.bottom, r.right, r.bottom),
            (r.left, r.top, r.left, r.bottom),
        ]

    @staticmethod
    def trace(origin, direction, mirrors, blockers, splitters, movers,
              beam_color='laser', depth=0, max_depth=5, reflective_walls=False):
        """
        Returns list of BeamSegment dicts.
        Each segment: {pts, color}
        Recursive for splitters.
        Walls terminate the beam unless reflective_walls=True.
        """
        if depth > max_depth:
            return []

        segments = []
        ox, oy = origin
        dx, dy = direction
        pts = [(ox, oy)]
        hit_objects = []

        walls = PhysicsEngine.room_walls()
        color_key = beam_color

        for _ in range(MAX_BOUNCES):
            nearest_t = float('inf')
            hit_type = None
            hit_ref = None
            hit_px, hit_py = 0, 0

            # Check mirrors
            for m in mirrors:
                p1, p2 = m.endpoints()
                res = V.ray_seg(ox, oy, dx, dy, *p1, *p2)
                if res and res[0] < nearest_t:
                    nearest_t, hit_px, hit_py = res
                    hit_type, hit_ref = 'mirror', m

            # Check splitters
            for sp in splitters:
                p1, p2 = sp.endpoints()
                res = V.ray_seg(ox, oy, dx, dy, *p1, *p2)
                if res and res[0] < nearest_t:
                    nearest_t, hit_px, hit_py = res
                    hit_type, hit_ref = 'splitter', sp

            # Check blockers
            for bl in blockers:
                res = V.ray_seg(ox, oy, dx, dy, bl.x1, bl.y1, bl.x2, bl.y2)
                if res and res[0] < nearest_t:
                    nearest_t, hit_px, hit_py = res
                    hit_type, hit_ref = 'blocker', bl

            # Check movers
            for mv in movers:
                p1, p2 = mv.endpoints()
                res = V.ray_seg(ox, oy, dx, dy, *p1, *p2)
                if res and res[0] < nearest_t:
                    nearest_t, hit_px, hit_py = res
                    hit_type, hit_ref = 'blocker', mv  # same as blocker

            # Check walls — always find nearest wall hit for clipping
            for wx1, wy1, wx2, wy2 in walls:
                res = V.ray_seg(ox, oy, dx, dy, wx1, wy1, wx2, wy2)
                if res and res[0] < nearest_t:
                    nearest_t, hit_px, hit_py = res
                    seg_dx = wx2 - wx1
                    seg_dy = wy2 - wy1
                    nx, ny = V.norm(-seg_dy, seg_dx)
                    hit_type = 'wall'
                    hit_ref = (nx, ny)

            if hit_type is None:
                # No intersection found — extend far (shouldn't happen inside room)
                px = ox + dx * 3000
                py = oy + dy * 3000
                pts.append((px, py))
                break

            pts.append((hit_px, hit_py))

            if hit_type == 'mirror':
                nx, ny = hit_ref.normal()
                if dx*nx + dy*ny > 0:
                    nx, ny = -nx, -ny
                dx, dy = V.reflect(dx, dy, nx, ny)
                ox, oy = hit_px, hit_py
                hit_objects.append(('mirror', hit_ref, hit_px, hit_py))

            elif hit_type == 'splitter':
                nx, ny = hit_ref.normal()
                if dx*nx + dy*ny > 0:
                    nx, ny = -nx, -ny
                rdx, rdy = V.reflect(dx, dy, nx, ny)
                # Segment ends here, recurse for reflected beam
                segments.append({'pts': pts[:], 'color': color_key})
                # Reflected sub-beam — pass reflective_walls through
                sub = PhysicsEngine.trace(
                    (hit_px, hit_py), (rdx, rdy),
                    mirrors, blockers, splitters, movers,
                    'laser2', depth+1, reflective_walls=reflective_walls
                )
                segments.extend(sub)
                # Transmitted beam continues
                pts = [(hit_px, hit_py)]
                ox, oy = hit_px, hit_py
                # dx, dy unchanged (pass-through)
                hit_objects.append(('splitter', hit_ref, hit_px, hit_py))

            elif hit_type == 'blocker':
                # Terminates beam
                break

            elif hit_type == 'wall':
                if reflective_walls:
                    # Reflect off wall
                    nx, ny = hit_ref
                    if dx*nx + dy*ny > 0:
                        nx, ny = -nx, -ny
                    dx, dy = V.reflect(dx, dy, nx, ny)
                    ox, oy = hit_px, hit_py
                else:
                    # Wall simply terminates the beam — stop here
                    break

        segments.append({'pts': pts, 'color': color_key})
        return segments

    @staticmethod
    def check_sensors(segments, sensors):
        """Returns set of sensor indices that are hit.
        Checks every point in every segment (endpoint and intermediate).
        Also checks if the beam passes close to any sensor mid-path.
        """
        hit_indices = set()
        for seg in segments:
            pts = seg['pts']
            if len(pts) < 2:
                continue
            # Check every consecutive pair of points for sensor proximity
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]
                x2, y2 = pts[i+1]
                for si, sensor in enumerate(sensors):
                    # Check endpoint
                    if V.dist(x2, y2, sensor.x, sensor.y) < TOLERANCE:
                        hit_indices.add(si)
                    # Also check if beam segment passes close to sensor
                    # (project sensor onto segment)
                    seg_len = V.dist(x1, y1, x2, y2)
                    if seg_len > 0:
                        t = ((sensor.x - x1)*(x2-x1) + (sensor.y - y1)*(y2-y1)) / (seg_len*seg_len)
                        t = max(0.0, min(1.0, t))
                        cx = x1 + t*(x2-x1)
                        cy = y1 + t*(y2-y1)
                        if V.dist(cx, cy, sensor.x, sensor.y) < TOLERANCE:
                            hit_indices.add(si)
        return hit_indices

# ═══════════════════════════════════════════════════════════════════════
# LEVEL DATA
# ═══════════════════════════════════════════════════════════════════════
def build_levels():
    """Returns list of level-factory callables"""

    def lv1():
        return {
            "name": "FIRST CONTACT",
            "description": "Guide the laser to the sensor",
            "origin": (ROOM.left, ROOM.top + 180),
            "direction": (1.0, 0.0),
            "mirrors": [
                Mirror(540, 240, 45, -180, 180, "M1"),
                Mirror(540, 480, -45, -180, 180, "M2"),
            ],
            "blockers": [],
            "splitters": [],
            "movers": [],
            "sensors": [Sensor(ROOM.right - 20, 480)],
            "reflective_walls": False,
            "hint": "Select a mirror, rotate with ← → arrows",
        }

    def lv2():
        return {
            "name": "NARROW PASSAGE",
            "description": "Route the beam around the obstacle",
            "origin": (ROOM.left, ROOM.top + 140),
            "direction": (1.0, 0.0),
            "mirrors": [
                Mirror(540, 200, 90, -180, 180, "M1"),
                Mirror(540, 480, 0, -180, 180, "M2"),
            ],
            "blockers": [
                Blocker(610, ROOM.top, 610, ROOM.top + 360),
            ],
            "splitters": [],
            "movers": [],
            "sensors": [Sensor(ROOM.right - 20, 480)],
            "reflective_walls": False,
            "hint": "Bend the beam DOWN then RIGHT to reach the sensor",
        }

    def lv3():
        return {
            "name": "SPLIT DECISION",
            "description": "Activate both sensors",
            "origin": (ROOM.left, ROOM.top + 300),
            "direction": (1.0, 0.0),
            "mirrors": [
                Mirror(520, 360, 45, -180, 180, "M1"),
                Mirror(700, 220, -50, -180, 180, "M2"),
            ],
            "blockers": [],
            "splitters": [
                Splitter(450, 360, -45),
            ],
            "movers": [],
            "sensors": [
                Sensor(ROOM.right - 20, 220, "SEN-A"),
                Sensor(ROOM.right - 20, 500, "SEN-B"),
            ],
            "reflective_walls": False,
            "hint": "The splitter creates TWO beams simultaneously",
        }

    def lv4():
        return {
            "name": "MOVING TARGET",
            "description": "Time the beam with the moving obstacle",
            "origin": (ROOM.left, ROOM.top + 200),
            "direction": (1.0, 0.0),
            "mirrors": [
                Mirror(500, 260, 45, -180, 180, "M1"),
                Mirror(700, 420, -50, -180, 180, "M2"),
            ],
            "blockers": [],
            "splitters": [],
            "movers": [
                MovingObstacle(580, 340, 580, 480, speed=0.012),
            ],
            "sensors": [Sensor(ROOM.right - 20, 420)],
            "reflective_walls": False,
            "hint": "Watch the moving obstacle's pattern before committing",
        }

    return [lv1, lv2, lv3, lv4]

# ═══════════════════════════════════════════════════════════════════════
# LEVEL (world state)
# ═══════════════════════════════════════════════════════════════════════
class Level:
    def __init__(self, data):
        self.name = data["name"]
        self.description = data["description"]
        self.origin = data["origin"]
        self.direction = data["direction"]
        self.mirrors = data["mirrors"]
        self.blockers = data["blockers"]
        self.splitters = data["splitters"]
        self.movers = data["movers"]
        self.sensors = data["sensors"]
        self.reflective_walls = data.get("reflective_walls", False)
        self.hint = data.get("hint", "")
        self.selected = None
        self.hovered = None
        self.segments = []
        self.all_hit = False

    def all_rotatables(self):
        return self.mirrors + self.splitters

    def select(self, obj):
        if self.selected:
            self.selected.selected = False
        self.selected = obj
        if obj:
            obj.selected = True

    def rotate_selected(self, delta, particles):
        if self.selected:
            old_angle = self.selected.angle
            self.selected.rotate(delta)
            if self.selected.angle != old_angle:
                particles.spark(self.selected.x, self.selected.y,
                                C["mirror_sel"], 5)

    def recompute(self):
        self.segments = PhysicsEngine.trace(
            self.origin, self.direction,
            self.mirrors, self.blockers, self.splitters, self.movers,
            reflective_walls=self.reflective_walls
        )
        hit_set = PhysicsEngine.check_sensors(self.segments, self.sensors)
        for i, s in enumerate(self.sensors):
            was = s.active
            s.active = (i in hit_set)
            if s.active and not was:
                s.hit_flash = 255
        self.all_hit = (len(hit_set) == len(self.sensors))

    def update(self, dt, particles):
        for mv in self.movers:
            mv.update()
        for s in self.sensors:
            s.update(dt)
        # Ambient particles on active sensors
        for s in self.sensors:
            if s.active and random.random() < 0.3:
                particles.ambient(s.x, s.y, C["sensor_on"])

    def hover_check(self, mx, my):
        self.hovered = None
        for obj in self.all_rotatables():
            obj.hovered = False
            if V.dist(mx, my, obj.x, obj.y) < 45:
                obj.hovered = True
                self.hovered = obj

# ═══════════════════════════════════════════════════════════════════════
# RENDERER
# ═══════════════════════════════════════════════════════════════════════
class Renderer:
    def __init__(self, screen):
        self.screen = screen
        self.font_lg = pygame.font.Font(None, 52)
        self.font_md = pygame.font.Font(None, 32)
        self.font_sm = pygame.font.Font(None, 22)
        self.font_xs = pygame.font.Font(None, 17)
        self.bg_stars = [(random.randint(0,W), random.randint(0,H),
                          random.uniform(0.3, 1.0)) for _ in range(180)]
        self.bg_t = 0.0

    def draw_bg(self, dt):
        self.bg_t += dt
        self.screen.fill(C["bg"])

        # Animated grid
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        grid_spacing = 60
        pulse = int(math.sin(self.bg_t * 0.7) * 4)
        for x in range(0, W, grid_spacing):
            a = 10 + pulse
            pygame.draw.line(gs, (20, 35, 80, a), (x, 0), (x, H), 1)
        for y in range(0, H, grid_spacing):
            a = 10 + pulse
            pygame.draw.line(gs, (20, 35, 80, a), (0, y), (W, y), 1)
        self.screen.blit(gs, (0,0))

        # Stars
        for sx, sy, brightness in self.bg_stars:
            a = int(80 * brightness * (0.7 + 0.3 * math.sin(self.bg_t + sx)))
            c = (a, a, int(a * 1.2))
            pygame.draw.circle(self.screen, c, (sx, sy), 1)

    def draw_room(self):
        # Room bg
        pygame.draw.rect(self.screen, C["room_bg"], ROOM, border_radius=4)
        # Room border glow
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*C["room_border"], 120), ROOM.inflate(6,6), 2, border_radius=6)
        pygame.draw.rect(gs, (*C["room_border"], 50), ROOM.inflate(14,14), 2, border_radius=8)
        self.screen.blit(gs, (0,0))
        pygame.draw.rect(self.screen, C["room_border"], ROOM, 2, border_radius=4)

        # ROOM label
        lbl = self.font_xs.render("SECURE ZONE", True, C["room_border"])
        self.screen.blit(lbl, (ROOM.left + 6, ROOM.top - 16))

    def draw_laser(self, segments):
        if not segments:
            return
        for seg in segments:
            pts = seg['pts']
            color_key = seg['color']
            lc = C[color_key]
            if len(pts) < 2:
                continue
            ipts = [(int(p[0]), int(p[1])) for p in pts]

            # Outer glow
            gs = pygame.Surface((W, H), pygame.SRCALPHA)
            if len(ipts) >= 2:
                pygame.draw.lines(gs, (*lc, 25), False, ipts, 18)
                pygame.draw.lines(gs, (*lc, 50), False, ipts, 10)
                pygame.draw.lines(gs, (*lc, 90), False, ipts, 5)
            self.screen.blit(gs, (0,0))

            # Core
            if len(ipts) >= 2:
                pygame.draw.lines(self.screen, lc, False, ipts, 2)

    def draw_objects(self, level):
        for bl in level.blockers:
            bl.draw(self.screen)
        for mv in level.movers:
            mv.draw(self.screen)
        for sp in level.splitters:
            sp.draw(self.screen, self.font_xs)
        for m in level.mirrors:
            m.draw(self.screen, self.font_xs)
        for s in level.sensors:
            s.draw(self.screen, self.font_xs)

        # Laser origin indicator
        ox, oy = level.origin
        pygame.draw.circle(self.screen, C["laser"], (int(ox), int(oy)), 7)
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.circle(gs, (*C["laser"], 80), (int(ox), int(oy)), 16)
        self.screen.blit(gs, (0,0))
        lbl = self.font_xs.render("SRC", True, C["laser"])
        self.screen.blit(lbl, (int(ox)+10, int(oy)-8))

    def draw_ui_panel(self, level, level_idx, total_levels):
        # Left panel
        panel = pygame.Rect(10, 60, 290, H - 80)
        pygame.draw.rect(self.screen, C["panel"], panel, border_radius=6)
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*C["panel_border"], 180), panel, 2, border_radius=6)
        self.screen.blit(gs, (0,0))

        y = panel.top + 18

        # Level name
        lvl_lbl = self.font_xs.render(f"LEVEL  {level_idx+1} / {total_levels}", True, C["text_dim"])
        self.screen.blit(lvl_lbl, (panel.left + 14, y))
        y += 22

        name = self.font_md.render(level.name, True, C["white"])
        self.screen.blit(name, (panel.left + 10, y))
        y += 36

        # Divider
        pygame.draw.line(self.screen, C["panel_border"],
                         (panel.left+10, y), (panel.right-10, y), 1)
        y += 14

        # Description
        desc_lines = self._wrap(level.description, self.font_xs, 260)
        for line in desc_lines:
            tl = self.font_xs.render(line, True, C["text_dim"])
            self.screen.blit(tl, (panel.left+14, y))
            y += 17
        y += 10

        # Sensors status
        sen_lbl = self.font_sm.render("SENSORS", True, C["text_dim"])
        self.screen.blit(sen_lbl, (panel.left+14, y))
        y += 22
        for i, s in enumerate(level.sensors):
            dot_c = C["sensor_on"] if s.active else C["sensor_off"]
            pygame.draw.circle(self.screen, dot_c, (panel.left+22, y+8), 6)
            st = "ARMED" if s.active else "INACTIVE"
            st_lbl = self.font_xs.render(f"{s.label}  —  {st}", True, dot_c)
            self.screen.blit(st_lbl, (panel.left+34, y))
            y += 22
        y += 10

        # Selected mirror info
        if level.selected:
            m = level.selected
            pygame.draw.line(self.screen, C["panel_border"],
                             (panel.left+10, y), (panel.right-10, y), 1)
            y += 14
            sel_lbl = self.font_sm.render("SELECTED", True, C["mirror_sel"])
            self.screen.blit(sel_lbl, (panel.left+14, y))
            y += 20
            angle_txt = self.font_xs.render(f"Angle:  {m.angle:.1f}°", True, C["text"])
            self.screen.blit(angle_txt, (panel.left+14, y))
            y += 17

        # Hint at bottom
        if level.hint:
            hint_y = panel.bottom - 60
            pygame.draw.line(self.screen, C["panel_border"],
                             (panel.left+10, hint_y-8), (panel.right-10, hint_y-8), 1)
            hint_lines = self._wrap("HINT: " + level.hint, self.font_xs, 260)
            for line in hint_lines:
                hl = self.font_xs.render(line, True, C["text_dim"])
                self.screen.blit(hl, (panel.left+14, hint_y))
                hint_y += 17

        # Controls help at top
        ctrl = self.font_xs.render("CLICK mirror · ← → rotate · R reset · ESC menu", True, C["text_dim"])
        self.screen.blit(ctrl, (ROOM.left, H - 22))

    def _wrap(self, text, font, max_w):
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            test = cur + (" " if cur else "") + w
            if font.size(test)[0] <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def draw_header(self, level_idx):
        title = self.font_md.render("PROJECT ABSOLUTE LIGHT", True, C["text"])
        self.screen.blit(title, (W//2 - title.get_width()//2, 14))
        # Decorative line
        lx = W//2 - 160
        pygame.draw.line(self.screen, C["room_border"], (lx, 44), (lx+320, 44), 1)

    def draw_particles(self, ps):
        ps.draw(self.screen)

    def draw_win_overlay(self, t):
        """Victory overlay, t: 0..1"""
        a = int(min(200, t * 400))
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 20, 10, a))
        self.screen.blit(ov, (0,0))

        if t > 0.3:
            ta = min(255, int((t-0.3)/0.7 * 255))
            txt1 = self.font_lg.render("ALARM DISABLED", True, (*C["sensor_on"], ta))
            txt2 = self.font_sm.render("Press SPACE to continue", True, (*C["text"], ta))
            self.screen.blit(txt1, (W//2 - txt1.get_width()//2, H//2 - 40))
            self.screen.blit(txt2, (W//2 - txt2.get_width()//2, H//2 + 20))

    def draw_menu(self, t, high_score):
        self.draw_bg(0)

        # Title
        title_y = H//2 - 160
        t1 = self.font_lg.render("PROJECT", True, C["text_dim"])
        t2 = pygame.font.Font(None, 88).render("ABSOLUTE LIGHT", True, C["white"])
        t3 = self.font_sm.render("LASER REFLECTION PUZZLE", True, C["text_dim"])
        self.screen.blit(t1, (W//2 - t1.get_width()//2, title_y))
        self.screen.blit(t2, (W//2 - t2.get_width()//2, title_y + 42))
        self.screen.blit(t3, (W//2 - t3.get_width()//2, title_y + 118))

        # Glow under title
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pulse = int(math.sin(t*2)*20)
        pygame.draw.ellipse(gs, (*C["laser"], 15),
                            (W//2-300, title_y+60, 600, 80+pulse))
        self.screen.blit(gs, (0,0))

        # Buttons
        btn_y = H//2 + 30
        self._menu_button("PLAY", W//2, btn_y, t)
        lbl = self.font_xs.render(f"Best Level Reached: {high_score}", True, C["text_dim"])
        self.screen.blit(lbl, (W//2 - lbl.get_width()//2, btn_y + 58))

        ctrl = self.font_xs.render("Select mirror → rotate with ← → arrow keys", True, C["text_dim"])
        self.screen.blit(ctrl, (W//2 - ctrl.get_width()//2, H - 40))

    def _menu_button(self, text, cx, cy, t):
        pulse = math.sin(t * 3) * 3
        w, h = 200, 50
        r = pygame.Rect(cx - w//2, cy - h//2, w, h)
        pygame.draw.rect(self.screen, (15, 25, 60), r, border_radius=6)
        pygame.draw.rect(self.screen, C["room_border"], r, 2, border_radius=6)
        # Hover glow
        gs = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(gs, (*C["room_border"], 40), r.inflate(int(pulse*2), int(pulse*2)), border_radius=8)
        self.screen.blit(gs, (0,0))
        lbl = self.font_md.render(text, True, C["white"])
        self.screen.blit(lbl, (cx - lbl.get_width()//2, cy - lbl.get_height()//2))
        return r

    def draw_level_complete(self, level_name, t):
        self.screen.fill(C["bg"])
        a = min(255, int(t * 600))

        # Stars / sparkles
        rs = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(40):
            sx = random.randint(0, W)
            sy = random.randint(0, H)
            sr = random.randint(1, 4)
            sa = random.randint(20, 100)
            pygame.draw.circle(rs, (*C["sensor_on"], sa), (sx, sy), sr)
        self.screen.blit(rs, (0,0))

        title = pygame.font.Font(None, 80).render("LEVEL COMPLETE", True, (*C["gold"], a))
        self.screen.blit(title, (W//2 - title.get_width()//2, H//2 - 120))

        sub = self.font_md.render(level_name, True, (*C["text"], a))
        self.screen.blit(sub, (W//2 - sub.get_width()//2, H//2 - 50))

        cont = self.font_sm.render("SPACE — Next Level", True, (*C["white"], a))
        self.screen.blit(cont, (W//2 - cont.get_width()//2, H//2 + 30))

# ═══════════════════════════════════════════════════════════════════════
# GAME STATES
# ═══════════════════════════════════════════════════════════════════════
class StateMenu:
    def __init__(self, game):
        self.game = game
        self.t = 0.0

    def update(self, dt, events):
        self.t += dt
        for e in events:
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.game.start_level(0)
            if e.type == pygame.MOUSEBUTTONDOWN:
                mx, my = pygame.mouse.get_pos()
                if W//2-100 <= mx <= W//2+100 and H//2+5 <= my <= H//2+45:
                    self.game.start_level(0)

    def draw(self, renderer):
        renderer.draw_menu(self.t, self.game.high_score)


class StatePlaying:
    def __init__(self, game, level, level_idx):
        self.game = game
        self.level = level
        self.level_idx = level_idx
        self.win_t = 0.0
        self.won = False
        self.particles = game.particles

    def update(self, dt, events):
        mx, my = pygame.mouse.get_pos()
        self.level.hover_check(mx, my)
        self.level.recompute()
        self.level.update(dt, self.particles)
        self.game.renderer.bg_t += dt

        if self.level.all_hit and not self.won:
            self.won = True
            self.win_t = 0.0
            # Big burst on all sensors
            for s in self.level.sensors:
                self.particles.glow_burst(s.x, s.y, C["sensor_on"], 30)

        if self.won:
            self.win_t += dt
            if self.win_t > 2.5:
                self.game.level_complete(self.level_idx)

        self.particles.update()

        for e in events:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.game.go_menu()
                elif e.key == pygame.K_r:
                    self.game.start_level(self.level_idx)
                elif e.key == pygame.K_LEFT and not self.won:
                    self.level.rotate_selected(-2, self.particles)
                elif e.key == pygame.K_RIGHT and not self.won:
                    self.level.rotate_selected(2, self.particles)

            if e.type == pygame.MOUSEBUTTONDOWN and not self.won:
                mx2, my2 = pygame.mouse.get_pos()
                clicked = None
                for obj in self.level.all_rotatables():
                    if V.dist(mx2, my2, obj.x, obj.y) < 45:
                        clicked = obj
                        break
                self.level.select(clicked)

    def draw(self, renderer):
        renderer.draw_bg(0)
        renderer.draw_header(self.level_idx)
        renderer.draw_room()
        renderer.draw_laser(self.level.segments)
        renderer.draw_objects(self.level)
        renderer.draw_particles(self.particles)
        renderer.draw_ui_panel(self.level, self.level_idx, len(self.game.level_factories))

        if self.won:
            renderer.draw_win_overlay(min(1.0, self.win_t / 2.0))


class StateLevelComplete:
    def __init__(self, game, level_name, next_idx):
        self.game = game
        self.level_name = level_name
        self.next_idx = next_idx
        self.t = 0.0

    def update(self, dt, events):
        self.t += dt
        for e in events:
            if e.type == pygame.KEYDOWN and e.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self.next_idx < len(self.game.level_factories):
                    self.game.start_level(self.next_idx)
                else:
                    self.game.go_menu()
            if e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                self.game.go_menu()

    def draw(self, renderer):
        renderer.draw_level_complete(self.level_name, self.t)


# ═══════════════════════════════════════════════════════════════════════
# GAME  (root driver)
# ═══════════════════════════════════════════════════════════════════════
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Project Absolute Light")
        self.clock = pygame.time.Clock()
        self.renderer = Renderer(self.screen)
        self.particles = ParticleSystem()
        self.level_factories = build_levels()
        self.state = None
        self.high_score = 1
        self.go_menu()

    def go_menu(self):
        self.state = StateMenu(self)

    def start_level(self, idx):
        if idx >= len(self.level_factories):
            self.go_menu()
            return
        data = self.level_factories[idx]()
        level = Level(data)
        self.particles = ParticleSystem()
        self.state = StatePlaying(self, level, idx)

    def level_complete(self, idx):
        level = self.state.level
        if idx + 1 > self.high_score:
            self.high_score = idx + 1
        self.state = StateLevelComplete(self, level.name, idx + 1)

    def run(self):
        prev = time.time()
        while True:
            now = time.time()
            dt = min(now - prev, 0.05)
            prev = now

            events = []
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                events.append(e)

            self.state.update(dt, events)
            self.state.draw(self.renderer)
            pygame.display.flip()
            self.clock.tick(FPS)


# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    Game().run()
