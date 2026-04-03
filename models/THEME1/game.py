import pygame
import math
import random
import sys
pygame.init()

# Display settings
WIDTH, HEIGHT = 1600, 900

# Constants
WATER_LEVEL = 250
FPS = 60

# Refractive indices
N_AIR = 1.0
N_WATER = 1.33

# Colors
WHITE = (255, 255, 255)
RED = (255, 80, 80)
GREEN = (80, 255, 80)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)

# Setup display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("FishingSpear")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 32)
small_font = pygame.font.Font(None, 22)

# Load images
sky_img = pygame.image.load("assets/sky.png").convert()
sea_img = pygame.image.load("assets/sea.png").convert()
boat_img = pygame.image.load("assets/boat.png").convert_alpha()
person_img = pygame.image.load("assets/person.png").convert_alpha()
fish_img = pygame.image.load("assets/fish.png").convert_alpha()

# Scale images
sky_img = pygame.transform.scale(sky_img, (WIDTH, WATER_LEVEL))
sea_img = pygame.transform.scale(sea_img, (WIDTH, HEIGHT - WATER_LEVEL))
boat_img = pygame.transform.scale(boat_img, (180, 80))
person_img = pygame.transform.scale(person_img, (60, 80))
fish_img = pygame.transform.scale(fish_img, (80, 40))

# Boat
boat_x = WIDTH // 2 - boat_img.get_width() // 2
boat_y = WATER_LEVEL - boat_img.get_height() + 10
boat_speed = 6

def get_observer():
    obs_x = boat_x + boat_img.get_width() // 2
    obs_y = boat_y - 20
    return obs_x, obs_y


class Fish:
    def __init__(self, x, y):
        self.real_x = x
        self.real_y = y
        self.base_y = y
        self.speed_x = random.choice([-1, 1]) * random.uniform(1.0, 2.0)

        self.wave_phase = random.uniform(0, math.pi * 2)
        self.wave_speed = random.uniform(0.03, 0.06)
        self.wave_amplitude = random.uniform(15, 30)

    def update(self):
        self.real_x += self.speed_x
        self.wave_phase += self.wave_speed
        self.real_y = self.base_y + math.sin(self.wave_phase) * self.wave_amplitude

        if self.real_x <= 40 or self.real_x >= WIDTH - 40:
            self.speed_x *= -1

        if self.real_y <= WATER_LEVEL + 40:
            self.base_y = WATER_LEVEL + 40 + self.wave_amplitude
        elif self.real_y >= HEIGHT - 40:
            self.base_y = HEIGHT - 40 - self.wave_amplitude

    def get_apparent_position(self, observer_x):
        depth_real = self.real_y - WATER_LEVEL
        depth_apparent = depth_real * (N_AIR / N_WATER)
        apparent_y = WATER_LEVEL + depth_apparent

        dx_real = self.real_x - observer_x
        dx_apparent = dx_real * (N_AIR / N_WATER)
        apparent_x = observer_x + dx_apparent

        return apparent_x, apparent_y

    def draw(self, surface, observer_x, real=False):
        if real:
            x, y = self.real_x, self.real_y
        else:
            x, y = self.get_apparent_position(observer_x)

        img = fish_img
        if self.speed_x < 0:
            img = pygame.transform.flip(fish_img, True, False)

        surface.blit(img, (int(x - img.get_width() // 2), int(y - img.get_height() // 2)))

    def get_rect_real(self):
        return pygame.Rect(
            int(self.real_x - fish_img.get_width() // 2),
            int(self.real_y - fish_img.get_height() // 2),
            fish_img.get_width(),
            fish_img.get_height()
        )

    def is_hit(self, x, y):
        return math.hypot(x - self.real_x, y - self.real_y) < 40


def calculate_real_position_from_apparent(click_x, click_y, observer_x):
    if click_y <= WATER_LEVEL:
        return click_x, click_y

    depth_apparent = click_y - WATER_LEVEL
    depth_real = depth_apparent * (N_WATER / N_AIR)
    real_y = WATER_LEVEL + depth_real

    dx_apparent = click_x - observer_x
    dx_real = dx_apparent * (N_WATER / N_AIR)
    real_x = observer_x + dx_real

    return real_x, real_y


def draw_refraction_ray(surface, obs, click_x, real_x, real_y):
    obs_x, obs_y = obs
    pygame.draw.line(surface, YELLOW, (obs_x, obs_y), (click_x, WATER_LEVEL), 3)
    pygame.draw.line(surface, GREEN, (click_x, WATER_LEVEL), (real_x, real_y), 3)


def draw_target(surface, x, y):
    pygame.draw.circle(surface, RED, (int(x), int(y)), 10, 2)
    pygame.draw.line(surface, RED, (x - 15, y), (x + 15, y), 2)
    pygame.draw.line(surface, RED, (x, y - 15), (x, y + 15), 2)


def sin_theta(dx, dy):
    length = math.hypot(dx, dy)
    if length == 0:
        return 0
    return abs(dx) / length  # angle with vertical normal


def main():
    global boat_x

    fish = Fish(WIDTH // 2, HEIGHT // 2)
    score = 0
    shots = 0

    show_ray = False
    ray_timer = 0
    ray_data = None

    show_real_timer = 0
    target_pos = None

    effect_text = ""
    effect_timer = 0
    effect_color = WHITE

    # For physics display
    sin_air = 0.0
    sin_water = 0.0
    h_value = 0.0

    Telemetry = False
    running = True
    while running:
        clock.tick(FPS)

        # Input
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            boat_x -= boat_speed
        if keys[pygame.K_RIGHT]:
            boat_x += boat_speed
        boat_x = max(0, min(WIDTH - boat_img.get_width(), boat_x))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    Telemetry = not Telemetry
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if my > WATER_LEVEL:
                    shots += 1
                    obs = get_observer()
                    real_x, real_y = calculate_real_position_from_apparent(mx, my, obs[0])

                    target_pos = (mx, my)

                    # Compute angles
                    # Air vector: observer -> surface point
                    dx_air = mx - obs[0]
                    dy_air = WATER_LEVEL - obs[1]

                    # Water vector: surface -> real point
                    dx_water = real_x - mx
                    dy_water = real_y - WATER_LEVEL

                    sin_air = sin_theta(dx_air, dy_air)
                    sin_water = sin_theta(dx_water, dy_water)

                    # h = real depth
                    h_value = fish.real_y - WATER_LEVEL

                    hit = fish.is_hit(real_x, real_y)

                    if hit:
                        score += 1
                        effect_text = "HIT! You Caught a Fish!"
                        effect_color = GREEN
                        fish = Fish(random.randint(100, WIDTH - 100),
                                    random.randint(WATER_LEVEL + 100, HEIGHT - 100))
                    else:
                        effect_text = "MISS! Better Luck Next Time!"
                        effect_color = RED

                    effect_timer = int(1.0 * FPS)

                    show_ray = True
                    ray_data = (obs, mx, real_x, real_y)
                    ray_timer = int(2.5 * FPS)
                    show_real_timer = int(1 * FPS)

        fish.update()

        if ray_timer > 0:
            ray_timer -= 1
        else:
            show_ray = False

        if show_real_timer > 0:
            show_real_timer -= 1

        if effect_timer > 0:
            effect_timer -= 1

        # Draw background
        screen.blit(sky_img, (0, 0))
        screen.blit(sea_img, (0, WATER_LEVEL))

        # Boat & person
        screen.blit(boat_img, (boat_x, boat_y))
        person_x = boat_x + boat_img.get_width() // 2 - person_img.get_width() // 2
        person_y = boat_y - person_img.get_height() + 30
        screen.blit(person_img, (person_x, person_y))

        obs = get_observer()

        # Fish apparent
        fish.draw(screen, obs[0], real=False)

        # Real fish auto-show + green rectangle
        if show_real_timer > 0:
            fish.draw(screen, obs[0], real=True)
            pygame.draw.rect(screen, GREEN, fish.get_rect_real(), 2)

        # Ray gun
        if show_ray and ray_data:
            draw_refraction_ray(screen, *ray_data)

        # Target icon
        if target_pos:
            draw_target(screen, target_pos[0], target_pos[1])

        # UI
        score_text = font.render(f"Score: {score}/{shots}", True, WHITE)
        screen.blit(score_text, (10, 10))

        # Coordinates, prob useless
        app_x, app_y = fish.get_apparent_position(obs[0])
        coord_lines = [
            f"Real: ({fish.real_x:.0f}, {fish.real_y:.0f})",
            f"Apparent: ({app_x:.0f}, {app_y:.0f})",
            f"h (real depth): {h_value:.1f}px",
            f"sin(theta_air): {sin_air:.4f}",
            f"sin(theta_water): {sin_water:.4f}",
        ]
        stats_toggle = small_font.render("Press Space to toggle stats",True,WHITE)
        screen.blit(stats_toggle ,(10 , 35))
        if Telemetry:
            for i, line in enumerate(coord_lines):
                t = small_font.render(line, True, WHITE)
                screen.blit(t, (10, 55 + i * 22))
        if score == 10:
            congrats_text = font.render("Congratulations! You are a Master Spearfisher!", True, WHITE)
            screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2, HEIGHT // 2 - 20))
        if score == 20:
            congrats_text = font.render("Unbelievable! You are a Legendary Spearfisher!", True, YELLOW)
            screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2, HEIGHT // 2 + 20))
        if score == 30:
            congrats_text = font.render("Incredible! You are a Mythical Spearfisher!", True, RED)
            screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2, HEIGHT // 2 + 60))
        if score == 40:
            congrats_text = font.render("Legendary! Most Impressive!", True, BLACK)
            screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2, HEIGHT // 2 + 100)) 
        if score == 50:
            congrats_text = font.render("Please Stop Tryharding , leave some fish for the rest of us", True, GREEN)
            screen.blit(congrats_text, (WIDTH // 2 - congrats_text.get_width() // 2 + 340, HEIGHT // 2 - 340))           
        # Hit / Miss
        if effect_timer > 0:
            txt = font.render(effect_text, True, effect_color)
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 20))
  
        pygame.display.flip()

    pygame.quit()
    sys.exit()


