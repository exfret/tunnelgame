import pygame

pygame.init()
screen = pygame.display.set_mode((1200, 750))
pygame.display.set_caption("Pygame CLI")
font = pygame.font.Font(None, 36)

keys_pressed = {}
input_text = ""

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                if input_text == "exit":
                    running = False
                input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            else:
                if event.unicode.isalnum() or event.unicode == " ":
                    input_text += event.unicode

    screen.fill((0, 0, 0))

    input_surface = font.render(f"> {input_text}", font, (255, 255, 255))
    screen.blit(input_surface, (20, -10 + screen.get_height() - font.get_height()))

    pygame.display.flip()

pygame.quit()
