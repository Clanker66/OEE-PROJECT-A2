import pygame
import sys
# ---------- Window Settings ----------
WIDTH ,HEIGHT = 1600 ,900

# ---------- Button settings ----------
BUTTON_WIDTH = 300
BUTTON_HEIGHT = 80
START_X = WIDTH // 2
START_Y = HEIGHT // 2 + 50

def run_menu(start_callback=None):
    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("FishingSpear")
    clock = pygame.time.Clock()

    # ---------- Load Background ----------
    bg = pygame.image.load("assets/background.png").convert_alpha()
    bg = pygame.transform.scale(bg, (WIDTH, HEIGHT))

    # ---------- Load Start Button ----------
    start_img = pygame.image.load("assets/Start1.png").convert_alpha()
    start_img = pygame.transform.scale(start_img, (BUTTON_WIDTH, BUTTON_HEIGHT))
    start_rect = start_img.get_rect(center=(START_X, START_Y))

    # ---------- Hover Effect ----------
    hover_alpha = 0
    HOVER_SPEED = 5
    MAX_HOVER_ALPHA = 100

    # ---------- Music ----------
    pygame.mixer.music.load("assets/music.mp3")
    pygame.mixer.music.play(-1)
    pygame.mixer.music.set_volume(0.25)
    sound_on = True

    # Mute button
    mute_width, mute_height = 80, 80
    mute_x, mute_y = WIDTH - mute_width - 20, HEIGHT - mute_height - 20
    mute_rect = pygame.Rect(mute_x, mute_y, mute_width, mute_height)

    music_on_img = pygame.image.load("assets/musicOn.png").convert_alpha()
    music_off_img = pygame.image.load("assets/musicOff.png").convert_alpha()
    music_on_img = pygame.transform.scale(music_on_img, (mute_width, mute_height))
    music_off_img = pygame.transform.scale(music_off_img, (mute_width, mute_height))

    running = True
    while running:
        screen.blit(bg, (0, 0))
        mouse = pygame.mouse.get_pos()
        click = pygame.mouse.get_pressed()

        # ---------- Draw Start Button ----------
        screen.blit(start_img, start_rect.topleft)

        # Hover effect
        if start_rect.collidepoint(mouse):
            hover_alpha = min(hover_alpha + HOVER_SPEED, MAX_HOVER_ALPHA)
            if click[0] and start_callback:
                pygame.mixer.music.stop()  # stop menu music
                start_callback()  # run the game
        else:
            hover_alpha = max(hover_alpha - HOVER_SPEED, 0)

        if hover_alpha > 0:
            overlay = pygame.Surface((BUTTON_WIDTH, BUTTON_HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 255, 255, hover_alpha))
            screen.blit(overlay, start_rect.topleft)

        # ---------- Mute button ----------
        if sound_on:
            screen.blit(music_on_img, mute_rect.topleft)
        else:
            screen.blit(music_off_img, mute_rect.topleft)

        if click[0] and mute_rect.collidepoint(mouse):
            sound_on = not sound_on
            if sound_on:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.pause()

        pygame.display.flip()
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

    pygame.quit()
    sys.exit()
