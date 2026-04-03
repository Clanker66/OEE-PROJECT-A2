import pygame
import menu
import game  # your friend's game file

# Run the menu
menu.run_menu(start_callback=game.main)
