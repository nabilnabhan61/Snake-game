import os
import random
import socket
import pygame
from dotenv import load_dotenv

GAME_WIDTH = 760
GAME_HEIGHT = 500
CHAT_PANEL_HEIGHT = 170
WINDOW_WIDTH = 920
WINDOW_HEIGHT = GAME_HEIGHT + CHAT_PANEL_HEIGHT
CELL_SIZE = 20
LOADING_SCREEN_SECONDS = 2.5

GAME_BACKGROUND_COLOR = (221, 211, 184)
GAME_BOARD_COLOR = (206, 197, 165)
GAME_BOARD_BORDER_COLOR = (86, 92, 67)
GAME_SIDE_PANEL_COLOR = (206, 197, 165)
GAME_SIDE_TEXT_COLOR = (49, 57, 42)
GAME_MUTED_TEXT_COLOR = (91, 99, 73)
BACKGROUND_COLOR = GAME_BACKGROUND_COLOR
BOARD_COLOR = GAME_BOARD_COLOR
BOARD_GRID_COLOR = GAME_BOARD_COLOR
PANEL_COLOR = GAME_SIDE_PANEL_COLOR
PANEL_BORDER_COLOR = GAME_BOARD_BORDER_COLOR
TEXT_COLOR = GAME_SIDE_TEXT_COLOR
MUTED_TEXT_COLOR = GAME_MUTED_TEXT_COLOR
ACCENT_COLOR = (118, 132, 79)
ACCENT_DARK_COLOR = GAME_BOARD_BORDER_COLOR
BUTTON_COLOR = (169, 160, 122)
BUTTON_ACTIVE_COLOR = (151, 145, 105)
BUTTON_DISABLED_COLOR = (202, 191, 156)
CHAT_PANEL_COLOR = (207, 194, 158)
INPUT_COLOR = (235, 222, 187)
OBSTACLE_COLOR = (129, 120, 92)
OBSTACLE_EDGE_COLOR = (91, 84, 65)
GAME_OBSTACLE_COLOR = (129, 120, 92)
GAME_OBSTACLE_EDGE_COLOR = (91, 84, 65)
GAME_OBSTACLE_LIGHT_COLOR = (164, 153, 118)

DESIGN_OPTIONS = ["red", "green", "blue", "yellow", "orange"]
KEY_FIELDS = ["up", "down", "left", "right"]


def send_message(client_socket, message):
    client_socket.sendall(f"{message}\n".encode())


def extract_messages(buffer):
    messages = []

    while "\n" in buffer:
        message, buffer = buffer.split("\n", 1)
        if message != "":
            messages.append(message)

    return messages, buffer


def get_snake_color(design):
    colors = {
        "red": (220, 76, 82),
        "green": (70, 184, 112),
        "blue": (76, 144, 221),
        "yellow": (228, 196, 74),
        "orange": (230, 132, 69),
    }

    return colors.get(design.lower(), (200, 200, 200))


def brighten_color(color, amount=35):
    return tuple(min(255, channel + amount) for channel in color)


def darken_color(color, amount=35):
    return tuple(max(0, channel - amount) for channel in color)


def draw_card(screen, rect):
    pygame.draw.rect(screen, PANEL_COLOR, rect, border_radius=10)
    pygame.draw.rect(screen, PANEL_BORDER_COLOR, rect, 2, border_radius=10)


def draw_loading_snake_picture(screen):
    picture = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    snake_points = [
        (95, 455),
        (190, 425),
        (285, 455),
        (380, 425),
        (475, 455),
        (570, 425),
        (665, 455),
        (760, 425),
    ]
    body_color = (118, 132, 79, 105)
    outline_color = (83, 92, 64, 95)

    for start_point, end_point in zip(snake_points, snake_points[1:]):
        pygame.draw.line(picture, outline_color, start_point, end_point, 48)
        pygame.draw.line(picture, body_color, start_point, end_point, 40)

    for point in snake_points:
        pygame.draw.circle(picture, outline_color, point, 24)
        pygame.draw.circle(picture, body_color, point, 20)

    head_center = snake_points[-1]
    pygame.draw.circle(picture, outline_color, head_center, 30)
    pygame.draw.circle(picture, (132, 148, 87, 135), head_center, 26)
    pygame.draw.circle(
        picture,
        (38, 45, 30, 150),
        (head_center[0] + 8, head_center[1] - 7),
        4,
    )
    pygame.draw.circle(
        picture,
        (38, 45, 30, 150),
        (head_center[0] + 10, head_center[1] + 7),
        4,
    )

    screen.blit(picture, (0, 0))


def draw_loading_screen(screen, font, big_font, elapsed_seconds):
    screen.fill(BACKGROUND_COLOR)
    draw_loading_snake_picture(screen)

    center_x = WINDOW_WIDTH // 2
    center_y = WINDOW_HEIGHT // 2
    card_rect = pygame.Rect(center_x - 230, center_y - 140, 460, 280)
    draw_card(screen, card_rect)

    title_surface = big_font.render("Snake Game", True, ACCENT_COLOR)
    title_rect = title_surface.get_rect(center=(center_x, center_y - 70))
    screen.blit(title_surface, title_rect)

    loading_text = "Loading" + "." * (int(elapsed_seconds * 2) % 4)
    loading_surface = font.render(loading_text, True, TEXT_COLOR)
    loading_rect = loading_surface.get_rect(center=(center_x, center_y - 15))
    screen.blit(loading_surface, loading_rect)

    bar_width = 260
    bar_height = 12
    bar_rect = pygame.Rect(
        center_x - bar_width // 2,
        center_y + 35,
        bar_width,
        bar_height,
    )
    progress = min(1, elapsed_seconds / LOADING_SCREEN_SECONDS)
    fill_rect = pygame.Rect(
        bar_rect.x,
        bar_rect.y,
        int(bar_width * progress),
        bar_height,
    )

    pygame.draw.rect(screen, INPUT_COLOR, bar_rect, border_radius=6)
    pygame.draw.rect(screen, ACCENT_COLOR, fill_rect, border_radius=6)
    pygame.draw.rect(screen, PANEL_BORDER_COLOR, bar_rect, 1, border_radius=6)

    hint_surface = font.render("Preparing multiplayer match", True, MUTED_TEXT_COLOR)
    hint_rect = hint_surface.get_rect(center=(center_x, center_y + 82))
    screen.blit(hint_surface, hint_rect)


def show_loading_screen(screen, clock, font, big_font):
    start_time = pygame.time.get_ticks()

    while True:
        elapsed_seconds = (pygame.time.get_ticks() - start_time) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

        draw_loading_screen(screen, font, big_font, elapsed_seconds)
        pygame.display.flip()

        if elapsed_seconds >= LOADING_SCREEN_SECONDS:
            return True

        clock.tick(60)


def handle_game_message(
    message,
    player_states,
    pie_positions,
    obstacle_positions,
    remaining_time,
    chat_messages,
    countdown_text,
    movement_active,
    game_over,
    winner_text,
    final_health_lines,
):
    if message.startswith("GAME_STATE:"):
        game_state_text = message[len("GAME_STATE:"):]
        parts = game_state_text.split("|")
        players_text = parts[0]
        pie_text = ""
        obstacles_text = ""
        time_text = "0"

        if len(parts) > 1:
            pie_text = parts[1]
        if len(parts) > 2:
            obstacles_text = parts[2]
        if len(parts) > 3:
            time_text = parts[3]

        player_states = {}

        if players_text != "":
            players = players_text.split(";")

            for player_data in players:
                player_parts = player_data.split(",")

                if len(player_parts) >= 5:
                    username, x, y, design, health = player_parts[:5]
                    body = [(int(x), int(y))]

                    if len(player_parts) >= 6 and player_parts[5] != "":
                        body = []
                        segment_texts = player_parts[5].split("~")

                        for segment_text in segment_texts:
                            segment_parts = segment_text.split(":")

                            if len(segment_parts) == 2:
                                body.append(
                                    (int(segment_parts[0]), int(segment_parts[1]))
                                )

                    if not body:
                        body = [(int(x), int(y))]

                    player_states[username] = {
                        "x": int(x),
                        "y": int(y),
                        "design": design,
                        "health": int(health),
                        "body": body,
                    }

        pie_positions = []
        if pie_text != "":
            pies = pie_text.split(";")

            for pie_data in pies:
                pie_parts = pie_data.split(",")

                if len(pie_parts) == 2:
                    pie_positions.append((int(pie_parts[0]), int(pie_parts[1])))

        obstacle_positions = []
        if obstacles_text != "":
            obstacles = obstacles_text.split(";")

            for obstacle_data in obstacles:
                obstacle_parts = obstacle_data.split(",")

                if len(obstacle_parts) >= 2:
                    obstacle_active = True

                    if len(obstacle_parts) >= 3:
                        obstacle_active = obstacle_parts[2] == "1"

                    obstacle_positions.append(
                        (
                            int(obstacle_parts[0]),
                            int(obstacle_parts[1]),
                            obstacle_active,
                        )
                    )

        try:
            remaining_time = int(time_text)
        except ValueError:
            remaining_time = 0

    elif message.startswith("COUNTDOWN:"):
        countdown_value = message[len("COUNTDOWN:"):]

        if countdown_value == "GO":
            countdown_text = "GO"
            movement_active = True
        else:
            countdown_text = f"Starting in {countdown_value}..."
            movement_active = False

    elif message.startswith("CHAT_FROM:"):
        chat_text = message[len("CHAT_FROM:"):]
        sender_parts = chat_text.split(":", 1)

        if len(sender_parts) == 2:
            sender, text = sender_parts
            chat_messages.append(f"{sender}: {text}")
            if len(chat_messages) > 5:
                chat_messages.pop(0)

    elif message.startswith("GAME_OVER:"):
        result_text = message[len("GAME_OVER:"):]
        parts = result_text.split("|")
        winner = parts[0]
        health_text = ""

        if len(parts) > 1:
            health_text = parts[1]

        game_over = True
        movement_active = False
        countdown_text = "Match finished"

        if winner == "DRAW":
            winner_text = "Draw"
        else:
            winner_text = f"Winner: {winner}"

        final_health_lines = []

        if health_text != "":
            players = health_text.split(";")

            for player_text in players:
                player_parts = player_text.split(",")

                if len(player_parts) == 2:
                    final_health_lines.append(
                        f"{player_parts[0]} health: {player_parts[1]}"
                    )

    return (
        player_states,
        pie_positions,
        obstacle_positions,
        remaining_time,
        chat_messages,
        countdown_text,
        movement_active,
        game_over,
        winner_text,
        final_health_lines,
    )


def draw_button(screen, font, rect, text, selected=False, enabled=True):
    color = BUTTON_COLOR

    if not enabled:
        color = BUTTON_DISABLED_COLOR
    elif selected:
        color = BUTTON_ACTIVE_COLOR

    pygame.draw.rect(screen, color, rect, border_radius=8)
    border_color = ACCENT_COLOR if selected and enabled else PANEL_BORDER_COLOR
    pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

    text_color = TEXT_COLOR if enabled else MUTED_TEXT_COLOR
    text_surface = font.render(text, True, text_color)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)


def draw_text_input(screen, font, rect, label, value, active):
    label_surface = font.render(label, True, MUTED_TEXT_COLOR)
    screen.blit(label_surface, (rect.x, rect.y - 30))

    box_color = INPUT_COLOR if active else BUTTON_COLOR
    border_color = ACCENT_COLOR if active else PANEL_BORDER_COLOR
    pygame.draw.rect(screen, box_color, rect, border_radius=8)
    pygame.draw.rect(screen, border_color, rect, 2, border_radius=8)

    display_value = value
    if active and pygame.time.get_ticks() % 1000 < 500:
        display_value += "|"

    text_surface = font.render(display_value, True, TEXT_COLOR)
    screen.blit(text_surface, (rect.x + 10, rect.y + 8))


def draw_pies(screen, pie_positions):
    if not pie_positions:
        return

    for pie_position in pie_positions:
        draw_pie(screen, pie_position)


def draw_pie(screen, pie_position):
    if pie_position is None:
        return

    pie_x, pie_y = pie_position
    center = (pie_x + CELL_SIZE // 2, pie_y + CELL_SIZE // 2)
    pygame.draw.circle(screen, (143, 77, 54), center, 9)
    pygame.draw.circle(screen, (208, 111, 72), center, 7)
    pygame.draw.circle(screen, (236, 170, 112), (center[0] - 3, center[1] - 3), 3)


def draw_snake(screen, player):
    body = player.get("body", [(player["x"], player["y"])])
    color = get_snake_color(player["design"])
    body_color = darken_color(color, 4)
    head_color = brighten_color(color, 10)
    outline_color = darken_color(color, 45)
    body_width = 18
    outline_width = 22

    centers = []
    for segment_x, segment_y in body:
        centers.append((segment_x + CELL_SIZE // 2, segment_y + CELL_SIZE // 2))

    path_points = []
    for index, center in enumerate(centers):
        if index == 0 or index == len(centers) - 1:
            path_points.append(center)
        else:
            previous_center = centers[index - 1]
            next_center = centers[index + 1]
            same_line = (
                previous_center[0] == center[0] == next_center[0]
                or previous_center[1] == center[1] == next_center[1]
            )

            if not same_line:
                path_points.append(center)

    if len(path_points) >= 2:
        pygame.draw.lines(screen, outline_color, False, path_points, outline_width)
        pygame.draw.lines(screen, body_color, False, path_points, body_width)

        for point in path_points[1:-1]:
            pygame.draw.circle(screen, outline_color, point, outline_width // 2)
            pygame.draw.circle(screen, body_color, point, body_width // 2)

    if centers:
        tail_center = centers[-1]
        pygame.draw.circle(screen, outline_color, tail_center, outline_width // 2)
        pygame.draw.circle(screen, body_color, tail_center, body_width // 2)

        head_center = centers[0]
        pygame.draw.circle(screen, outline_color, head_center, outline_width // 2 + 2)
        pygame.draw.circle(screen, head_color, head_center, body_width // 2 + 2)

        eye_color = (32, 38, 28)
        pygame.draw.circle(
            screen,
            eye_color,
            (head_center[0] - 4, head_center[1] - 3),
            2,
        )
        pygame.draw.circle(
            screen,
            eye_color,
            (head_center[0] + 4, head_center[1] - 3),
            2,
        )


def draw_obstacle(screen, obstacle_x, obstacle_y, active=True):
    obstacle_rect = pygame.Rect(obstacle_x + 2, obstacle_y + 3, 16, 15)
    shadow_rect = pygame.Rect(obstacle_x + 4, obstacle_y + 6, 14, 12)

    if not active:
        faded_color = (184, 176, 143)
        faded_edge_color = (150, 142, 112)
        pygame.draw.rect(screen, faded_color, obstacle_rect, border_radius=7)
        pygame.draw.rect(
            screen,
            faded_edge_color,
            obstacle_rect,
            1,
            border_radius=7,
        )
        return

    pygame.draw.rect(screen, (111, 103, 78), shadow_rect, border_radius=7)
    pygame.draw.rect(screen, GAME_OBSTACLE_COLOR, obstacle_rect, border_radius=7)
    pygame.draw.rect(
        screen,
        GAME_OBSTACLE_EDGE_COLOR,
        obstacle_rect,
        1,
        border_radius=7,
    )
    pygame.draw.circle(
        screen,
        GAME_OBSTACLE_LIGHT_COLOR,
        (obstacle_x + 8, obstacle_y + 8),
        3,
    )


def get_confetti_buttons(player_states):
    buttons = {}
    side_y = 110

    for username in player_states:
        buttons[username] = pygame.Rect(GAME_WIDTH + 74, side_y - 4, 76, 24)
        side_y += 62

    return buttons


def create_confetti_burst(player_states, target_username):
    if target_username not in player_states:
        return None

    player = player_states[target_username]
    body = player.get("body", [(player["x"], player["y"])])

    if body:
        head_x, head_y = body[0]
    else:
        head_x = player["x"]
        head_y = player["y"]

    base_color = get_snake_color(player["design"])
    colors = [
        base_color,
        brighten_color(base_color, 35),
        darken_color(base_color, 25),
    ]
    particles = []

    for _ in range(18):
        particles.append(
            {
                "x": head_x + CELL_SIZE // 2,
                "y": head_y + CELL_SIZE // 2,
                "vx": random.uniform(-1.4, 1.4),
                "vy": random.uniform(-2.0, 0.5),
                "color": random.choice(colors),
            }
        )

    return {
        "start": pygame.time.get_ticks(),
        "particles": particles,
    }


def update_confetti_bursts(confetti_bursts):
    now = pygame.time.get_ticks()
    active_bursts = []

    for burst in confetti_bursts:
        if now - burst["start"] < 1000:
            active_bursts.append(burst)

    return active_bursts


def draw_confetti_bursts(screen, confetti_bursts):
    now = pygame.time.get_ticks()

    for burst in confetti_bursts:
        age = (now - burst["start"]) / 1000

        for particle in burst["particles"]:
            particle_x = int(particle["x"] + particle["vx"] * age * 45)
            particle_y = int(
                particle["y"] + particle["vy"] * age * 45 + age * age * 35
            )

            if 0 <= particle_x < GAME_WIDTH and 0 <= particle_y < GAME_HEIGHT:
                pygame.draw.rect(
                    screen,
                    particle["color"],
                    (particle_x, particle_y, 4, 4),
                )


def draw_game_view(
    screen,
    font,
    small_font,
    big_font,
    player_states,
    pie_positions,
    obstacle_positions,
    remaining_time,
    chat_messages,
    chat_input,
    typing_chat,
    countdown_text,
    game_over,
    winner_text,
    final_health_lines,
    spectator_mode,
    confetti_button_rects,
    confetti_bursts,
    return_button_rect,
):
    screen.fill(GAME_BACKGROUND_COLOR)

    board_rect = pygame.Rect(0, 0, GAME_WIDTH, GAME_HEIGHT)
    pygame.draw.rect(screen, GAME_BOARD_COLOR, board_rect)
    pygame.draw.rect(screen, GAME_BOARD_BORDER_COLOR, board_rect, 4)

    if WINDOW_WIDTH > GAME_WIDTH:
        side_rect = pygame.Rect(GAME_WIDTH, 0, WINDOW_WIDTH - GAME_WIDTH, GAME_HEIGHT)
        pygame.draw.rect(screen, GAME_SIDE_PANEL_COLOR, side_rect)
        pygame.draw.line(
            screen,
            GAME_BOARD_BORDER_COLOR,
            (GAME_WIDTH, 0),
            (GAME_WIDTH, GAME_HEIGHT),
            3,
        )

        side_title = font.render("Match", True, GAME_SIDE_TEXT_COLOR)
        screen.blit(side_title, (GAME_WIDTH + 18, 24))

        side_time = small_font.render(
            f"Time: {remaining_time}",
            True,
            GAME_SIDE_TEXT_COLOR,
        )
        screen.blit(side_time, (GAME_WIDTH + 18, 62))

        side_y = 110
        for username in player_states:
            player = player_states[username]
            color = get_snake_color(player["design"])
            pygame.draw.circle(screen, color, (GAME_WIDTH + 26, side_y + 8), 6)

            name_surface = small_font.render(username, True, GAME_SIDE_TEXT_COLOR)
            screen.blit(name_surface, (GAME_WIDTH + 40, side_y))

            if spectator_mode and username in confetti_button_rects:
                draw_button(
                    screen,
                    small_font,
                    confetti_button_rects[username],
                    "Confetti",
                )

            health_surface = small_font.render(
                f"Health {player['health']}",
                True,
                GAME_MUTED_TEXT_COLOR,
            )
            screen.blit(health_surface, (GAME_WIDTH + 18, side_y + 24))
            side_y += 62

    for obstacle_data in obstacle_positions:
        obstacle_x = obstacle_data[0]
        obstacle_y = obstacle_data[1]
        obstacle_active = True

        if len(obstacle_data) >= 3:
            obstacle_active = obstacle_data[2]

        draw_obstacle(screen, obstacle_x, obstacle_y, obstacle_active)

    draw_pies(screen, pie_positions)

    for username in player_states:
        player = player_states[username]
        draw_snake(screen, player)

    draw_confetti_bursts(screen, confetti_bursts)

    if countdown_text != "" and not game_over:
        countdown_surface = big_font.render(
            countdown_text,
            True,
            GAME_SIDE_TEXT_COLOR,
        )
        countdown_rect = countdown_surface.get_rect(center=(GAME_WIDTH // 2, 72))
        screen.blit(countdown_surface, countdown_rect)

    if spectator_mode:
        spectator_surface = small_font.render(
            "Spectator Mode",
            True,
            GAME_SIDE_TEXT_COLOR,
        )
        screen.blit(spectator_surface, (14, GAME_HEIGHT - 28))

    if game_over:
        overlay_rect = pygame.Rect(GAME_WIDTH // 2 - 200, 150, 400, 185)
        pygame.draw.rect(screen, GAME_SIDE_PANEL_COLOR, overlay_rect, border_radius=10)
        pygame.draw.rect(
            screen,
            GAME_BOARD_BORDER_COLOR,
            overlay_rect,
            2,
            border_radius=10,
        )

        game_over_surface = big_font.render(
            winner_text,
            True,
            GAME_SIDE_TEXT_COLOR,
        )
        game_over_rect = game_over_surface.get_rect(center=(GAME_WIDTH // 2, 190))
        screen.blit(game_over_surface, game_over_rect)

        final_text_y = 223
        for line in final_health_lines:
            health_surface = font.render(line, True, GAME_SIDE_TEXT_COLOR)
            health_rect = health_surface.get_rect(center=(GAME_WIDTH // 2, final_text_y))
            screen.blit(health_surface, health_rect)
            final_text_y += 26

        draw_button(screen, font, return_button_rect, "Return to Lobby")

    pygame.draw.rect(
        screen,
        CHAT_PANEL_COLOR,
        (0, GAME_HEIGHT, WINDOW_WIDTH, CHAT_PANEL_HEIGHT),
    )
    pygame.draw.line(
        screen,
        PANEL_BORDER_COLOR,
        (0, GAME_HEIGHT),
        (WINDOW_WIDTH, GAME_HEIGHT),
        2,
    )

    if spectator_mode:
        spectator_title = font.render("Spectator Mode", True, TEXT_COLOR)
        spectator_text = small_font.render(
            "Watching the current match",
            True,
            MUTED_TEXT_COLOR,
        )
        screen.blit(spectator_title, (20, GAME_HEIGHT + 20))
        screen.blit(spectator_text, (20, GAME_HEIGHT + 55))
    else:
        chat_title = font.render("Chat", True, TEXT_COLOR)
        screen.blit(chat_title, (20, GAME_HEIGHT + 12))

        chat_y = GAME_HEIGHT + 42
        for chat_message in chat_messages:
            chat_surface = small_font.render(chat_message, True, TEXT_COLOR)
            screen.blit(chat_surface, (20, chat_y))
            chat_y += 20

        input_rect = pygame.Rect(15, GAME_HEIGHT + 125, WINDOW_WIDTH - 30, 30)
        pygame.draw.rect(screen, INPUT_COLOR, input_rect, border_radius=8)
        pygame.draw.rect(screen, PANEL_BORDER_COLOR, input_rect, 1, border_radius=8)

        if typing_chat:
            input_surface = font.render(f"> {chat_input}", True, ACCENT_COLOR)
        else:
            input_surface = font.render(
                "Press Enter to chat",
                True,
                MUTED_TEXT_COLOR,
            )

        screen.blit(input_surface, (24, GAME_HEIGHT + 131))


def main():
    load_dotenv()

    server_ip = os.getenv("SERVER_IP")
    server_port = os.getenv("SERVER_PORT")

    if server_ip is None or server_port is None:
        print("Missing SERVER_IP or SERVER_PORT in .env")
        return

    try:
        server_port = int(server_port)
    except ValueError:
        print("SERVER_PORT must be an integer")
        return

    pygame.init()

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Snake Game")

    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 28)
    small_font = pygame.font.Font(None, 24)
    big_font = pygame.font.Font(None, 42)

    if not show_loading_screen(screen, clock, font, big_font):
        pygame.quit()
        return

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        client_socket.connect((server_ip, server_port))
    except Exception as e:
        print(f"Connection failed: {e}")
        pygame.quit()
        return

    client_socket.settimeout(0.01)

    username = ""
    username_sent = False
    username_submitted = False
    username_error = ""

    current_screen = "username"
    status_message = "Enter your username to join"
    recv_buffer = ""

    online_users = []
    selected_opponent = None
    pending_opponent = None
    active_match_text = None

    snake_design = "green"
    movement_keys = {
        "up": "",
        "down": "",
        "left": "",
        "right": "",
    }
    selected_key_field = None
    snake_setup_sent = False

    spectator_mode = False
    match_confirmed = False
    both_ready = False

    player_states = {}
    pie_positions = []
    obstacle_positions = []
    remaining_time = 0
    chat_messages = []
    chat_input = ""
    typing_chat = False
    countdown_text = "Waiting for countdown..."
    movement_active = False
    game_over = False
    winner_text = ""
    final_health_lines = []
    confetti_bursts = []

    def reset_game_view_state():
        nonlocal spectator_mode
        nonlocal match_confirmed
        nonlocal both_ready
        nonlocal selected_opponent
        nonlocal pending_opponent
        nonlocal active_match_text
        nonlocal snake_setup_sent
        nonlocal selected_key_field
        nonlocal player_states
        nonlocal pie_positions
        nonlocal obstacle_positions
        nonlocal remaining_time
        nonlocal chat_messages
        nonlocal chat_input
        nonlocal typing_chat
        nonlocal countdown_text
        nonlocal movement_active
        nonlocal game_over
        nonlocal winner_text
        nonlocal final_health_lines
        nonlocal confetti_bursts
        nonlocal status_message

        spectator_mode = False
        match_confirmed = False
        both_ready = False
        selected_opponent = None
        pending_opponent = None
        active_match_text = None
        snake_setup_sent = False
        selected_key_field = None
        player_states = {}
        pie_positions = []
        obstacle_positions = []
        remaining_time = 0
        chat_messages = []
        chat_input = ""
        typing_chat = False
        countdown_text = "Waiting for countdown..."
        movement_active = False
        game_over = False
        winner_text = ""
        final_health_lines = []
        confetti_bursts = []
        status_message = "Choose a player to start a match"

    running = True

    while running:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                status_message = "Disconnected from server"
                if current_screen != "game":
                    current_screen = "lobby"
            else:
                recv_buffer += data
        except socket.timeout:
            pass
        except Exception:
            status_message = "Connection lost"

        messages, recv_buffer = extract_messages(recv_buffer)

        for message in messages:
            if message == "Username accepted":
                username_sent = True
                username_submitted = False
                username_error = ""
                current_screen = "lobby"
                status_message = "Choose a player to start a match"

            elif message == "Username already in use":
                username_submitted = False
                username_error = "Username already in use. Try another username."
                status_message = username_error

            elif message == "Invalid username":
                username_submitted = False
                username_error = "Enter a username before joining."
                status_message = username_error

            elif message.startswith("ONLINE_USERS:"):
                users_text = message[len("ONLINE_USERS:"):]

                if users_text == "":
                    online_users = []
                else:
                    online_users = users_text.split(",")

            elif message.startswith("MATCH_ACTIVE:"):
                active_match_text = message[len("MATCH_ACTIVE:"):]

                if current_screen == "lobby":
                    status_message = (
                        "A match is active. You can spectate from the lobby."
                    )

            elif message == "NO_ACTIVE_MATCH":
                active_match_text = None

                if current_screen == "lobby":
                    status_message = "Choose a player to start a match"

            elif message.startswith("MATCH_PENDING:"):
                pending_opponent = message[len("MATCH_PENDING:"):]
                selected_opponent = pending_opponent
                current_screen = "lobby"
                status_message = f"Waiting for {pending_opponent} to confirm the match"

            elif message.startswith("MATCH_CONFIRMED:"):
                match_info = message[len("MATCH_CONFIRMED:"):].split(":")

                if len(match_info) == 2:
                    player_one, player_two = match_info
                    active_match_text = f"{player_one},{player_two}"

                match_confirmed = True
                spectator_mode = False
                current_screen = "setup"
                status_message = "Choose your snake design and movement keys"

            elif message == "Invalid opponent":
                selected_opponent = None
                status_message = "Invalid opponent"

            elif message == "Opponent not available":
                selected_opponent = None
                status_message = "Opponent not available"

            elif message == "Match already active":
                selected_opponent = None
                status_message = "A match is already active. Spectate from the lobby."

            elif message == "SNAKE_SETUP_ACCEPTED":
                snake_setup_sent = True
                current_screen = "waiting"
                status_message = "Setup accepted. Waiting for both players to be ready."

            elif message == "INVALID_SNAKE_SETUP":
                snake_setup_sent = False
                current_screen = "setup"
                status_message = "Invalid setup. Use four different single keys."

            elif message == "BOTH_READY":
                both_ready = True
                current_screen = "game"
                status_message = "Both players are ready"

            elif message == "SPECTATE_ACCEPTED":
                spectator_mode = True
                current_screen = "game"
                status_message = "Spectator mode started"

            elif message == "ALREADY_PLAYING":
                status_message = "You are already one of the players in the match"

            elif message.startswith("ARENA_CONFETTI:"):
                target_username = message[len("ARENA_CONFETTI:"):]
                confetti_burst = create_confetti_burst(
                    player_states,
                    target_username,
                )

                if confetti_burst is not None:
                    confetti_bursts.append(confetti_burst)

            else:
                (
                    player_states,
                    pie_positions,
                    obstacle_positions,
                    remaining_time,
                    chat_messages,
                    countdown_text,
                    movement_active,
                    game_over,
                    winner_text,
                    final_health_lines,
                ) = handle_game_message(
                    message,
                    player_states,
                    pie_positions,
                    obstacle_positions,
                    remaining_time,
                    chat_messages,
                    countdown_text,
                    movement_active,
                    game_over,
                    winner_text,
                    final_health_lines,
                )

                if current_screen == "waiting" and countdown_text != "Waiting for countdown...":
                    current_screen = "game"

        username_box = pygame.Rect(WINDOW_WIDTH // 2 - 130, 205, 260, 42)
        username_button = pygame.Rect(WINDOW_WIDTH // 2 - 65, 270, 130, 40)

        opponent_buttons = []
        spectate_button = pygame.Rect(WINDOW_WIDTH - 250, 470, 180, 40)
        return_to_lobby_button = pygame.Rect(GAME_WIDTH // 2 - 90, 290, 180, 36)
        confetti_button_rects = {}

        if current_screen == "game" and spectator_mode:
            confetti_button_rects = get_confetti_buttons(player_states)

        if current_screen == "lobby" and active_match_text is None:
            other_players = []
            for player in online_users:
                if player != username:
                    other_players.append(player)

            button_y = 200
            for opponent_name in other_players:
                button_rect = pygame.Rect(50, button_y, 320, 42)
                opponent_buttons.append((opponent_name, button_rect))
                button_y += 55

        design_buttons = []
        key_boxes = {}
        setup_button = pygame.Rect(WINDOW_WIDTH // 2 - 90, 470, 180, 40)

        if current_screen == "setup":
            design_x = 50
            for design_name in DESIGN_OPTIONS:
                button_rect = pygame.Rect(design_x, 175, 115, 42)
                design_buttons.append((design_name, button_rect))
                design_x += 130

            box_y = 295
            for field_name in KEY_FIELDS:
                key_boxes[field_name] = pygame.Rect(200, box_y, 110, 42)
                box_y += 50

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif current_screen == "username":
                if event.type == pygame.KEYDOWN and not username_submitted:
                    if event.key == pygame.K_BACKSPACE:
                        username = username[:-1]
                    elif event.key == pygame.K_RETURN:
                        if username.strip() != "":
                            send_message(client_socket, username.strip())
                            username_submitted = True
                            status_message = "Waiting for server response..."
                    else:
                        if event.unicode.isprintable() and len(username) < 16:
                            username += event.unicode

                elif event.type == pygame.MOUSEBUTTONDOWN and not username_submitted:
                    if username_button.collidepoint(event.pos) and username.strip() != "":
                        send_message(client_socket, username.strip())
                        username_submitted = True
                        status_message = "Waiting for server response..."

            elif current_screen == "lobby":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if active_match_text is None:
                        for opponent_name, button_rect in opponent_buttons:
                            if button_rect.collidepoint(event.pos):
                                selected_opponent = opponent_name
                                pending_opponent = None
                                send_message(
                                    client_socket,
                                    f"SELECT_OPPONENT:{selected_opponent}",
                                )
                                status_message = (
                                    f"Match request sent to {selected_opponent}"
                                )
                    elif spectate_button.collidepoint(event.pos):
                        send_message(client_socket, "SPECTATE")
                        status_message = "Requesting spectator mode..."

            elif current_screen == "setup":
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for design_name, button_rect in design_buttons:
                        if button_rect.collidepoint(event.pos):
                            snake_design = design_name

                    for field_name, box_rect in key_boxes.items():
                        if box_rect.collidepoint(event.pos):
                            selected_key_field = field_name

                    if setup_button.collidepoint(event.pos):
                        filled_keys = [movement_keys[field] for field in KEY_FIELDS]

                        if (
                            all(filled_keys)
                            and len(set(filled_keys)) == 4
                            and snake_design != ""
                        ):
                            send_message(
                                client_socket,
                                (
                                    "SNAKE_SETUP:"
                                    f"{snake_design}|"
                                    f"{movement_keys['up']}|"
                                    f"{movement_keys['down']}|"
                                    f"{movement_keys['left']}|"
                                    f"{movement_keys['right']}"
                                ),
                            )
                            status_message = "Sending snake setup..."
                        else:
                            status_message = "Choose a design and four different keys."

                elif event.type == pygame.KEYDOWN and selected_key_field is not None:
                    if event.key == pygame.K_ESCAPE:
                        selected_key_field = None
                    elif event.key == pygame.K_BACKSPACE:
                        movement_keys[selected_key_field] = ""
                    else:
                        key_value = event.unicode.lower()

                        if len(key_value) == 1 and key_value.isprintable():
                            movement_keys[selected_key_field] = key_value
                            selected_key_field = None

            elif current_screen == "game":
                if event.type == pygame.MOUSEBUTTONDOWN and game_over:
                    if return_to_lobby_button.collidepoint(event.pos):
                        send_message(client_socket, "RETURN_TO_LOBBY")
                        reset_game_view_state()
                        current_screen = "lobby"

                elif event.type == pygame.MOUSEBUTTONDOWN and spectator_mode:
                    for target_username, button_rect in confetti_button_rects.items():
                        if button_rect.collidepoint(event.pos):
                            send_message(
                                client_socket,
                                f"CHEER_CONFETTI:{target_username}",
                            )

                elif event.type == pygame.KEYDOWN and not spectator_mode:
                    if typing_chat:
                        if event.key == pygame.K_RETURN:
                            if chat_input.strip() != "":
                                send_message(client_socket, f"CHAT:{chat_input}")
                                chat_messages.append(f"You: {chat_input}")
                                if len(chat_messages) > 5:
                                    chat_messages.pop(0)

                            chat_input = ""
                            typing_chat = False

                        elif event.key == pygame.K_BACKSPACE:
                            chat_input = chat_input[:-1]

                        elif event.key == pygame.K_ESCAPE:
                            chat_input = ""
                            typing_chat = False

                        else:
                            if event.unicode.isprintable():
                                chat_input += event.unicode

                    else:
                        if event.key == pygame.K_RETURN:
                            typing_chat = True

                        elif not game_over and movement_active:
                            pressed_key = event.unicode.lower()
                            command = None

                            if pressed_key == movement_keys["up"]:
                                command = "UP"
                            elif pressed_key == movement_keys["down"]:
                                command = "DOWN"
                            elif pressed_key == movement_keys["left"]:
                                command = "LEFT"
                            elif pressed_key == movement_keys["right"]:
                                command = "RIGHT"

                            if command is not None:
                                send_message(client_socket, f"DIRECTION:{command}")

            if event.type == pygame.QUIT:
                running = False

        confetti_bursts = update_confetti_bursts(confetti_bursts)

        screen.fill(BACKGROUND_COLOR)

        if current_screen == "username":
            draw_card(screen, pygame.Rect(WINDOW_WIDTH // 2 - 230, 55, 460, 365))

            title_surface = big_font.render("Snake Game", True, ACCENT_COLOR)
            title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, 105))
            screen.blit(title_surface, title_rect)

            subtitle_surface = font.render(
                "Enter your username to connect",
                True,
                MUTED_TEXT_COLOR,
            )
            subtitle_rect = subtitle_surface.get_rect(center=(WINDOW_WIDTH // 2, 150))
            screen.blit(subtitle_surface, subtitle_rect)

            draw_text_input(
                screen,
                font,
                username_box,
                "Username",
                username,
                True,
            )
            draw_button(
                screen,
                font,
                username_button,
                "Join",
                enabled=not username_submitted and username.strip() != "",
            )

            info_surface = small_font.render(status_message, True, MUTED_TEXT_COLOR)
            info_rect = info_surface.get_rect(center=(WINDOW_WIDTH // 2, 340))
            screen.blit(info_surface, info_rect)

            if username_error != "":
                error_surface = small_font.render(username_error, True, ACCENT_COLOR)
                error_rect = error_surface.get_rect(center=(WINDOW_WIDTH // 2, 372))
                screen.blit(error_surface, error_rect)

        elif current_screen == "lobby":
            draw_card(screen, pygame.Rect(30, 20, WINDOW_WIDTH - 60, 510))

            title_surface = big_font.render("Lobby", True, ACCENT_COLOR)
            screen.blit(title_surface, (50, 35))

            name_surface = small_font.render(
                f"Player: {username}",
                True,
                MUTED_TEXT_COLOR,
            )
            screen.blit(name_surface, (50, 80))

            status_surface = small_font.render(status_message, True, ACCENT_COLOR)
            screen.blit(status_surface, (50, 110))

            if active_match_text is not None:
                match_players = active_match_text.replace(",", " vs ")
                active_surface = font.render(
                    f"Active match: {match_players}",
                    True,
                    TEXT_COLOR,
                )
                screen.blit(active_surface, (50, 180))

                spectate_label = small_font.render(
                    "You can watch the current match.",
                    True,
                    MUTED_TEXT_COLOR,
                )
                screen.blit(spectate_label, (50, 220))

                draw_button(screen, font, spectate_button, "Spectate")
            else:
                list_title = font.render("Online Players", True, TEXT_COLOR)
                screen.blit(list_title, (50, 160))

                if len(opponent_buttons) == 0:
                    empty_surface = small_font.render(
                        "Waiting for another user to join...",
                        True,
                        MUTED_TEXT_COLOR,
                    )
                    screen.blit(empty_surface, (50, 205))
                else:
                    for opponent_name, button_rect in opponent_buttons:
                        draw_button(
                            screen,
                            font,
                            button_rect,
                            opponent_name,
                            selected=selected_opponent == opponent_name,
                        )

            if pending_opponent is not None:
                pending_surface = font.render(
                    f"Waiting for {pending_opponent} to confirm...",
                    True,
                    TEXT_COLOR,
                )
                screen.blit(pending_surface, (50, 410))

        elif current_screen == "setup":
            draw_card(screen, pygame.Rect(30, 20, WINDOW_WIDTH - 60, 510))

            title_surface = big_font.render("Snake Setup", True, ACCENT_COLOR)
            screen.blit(title_surface, (50, 35))

            info_surface = small_font.render(status_message, True, ACCENT_COLOR)
            screen.blit(info_surface, (50, 85))

            design_title = font.render("Choose a snake design", True, TEXT_COLOR)
            screen.blit(design_title, (50, 135))

            for design_name, button_rect in design_buttons:
                draw_button(
                    screen,
                    font,
                    button_rect,
                    f"  {design_name.capitalize()}",
                    selected=snake_design == design_name,
                )
                pygame.draw.circle(
                    screen,
                    get_snake_color(design_name),
                    (button_rect.x + 16, button_rect.centery),
                    7,
                )

            keys_title = font.render("Choose movement keys", True, TEXT_COLOR)
            screen.blit(keys_title, (50, 255))

            for field_name in KEY_FIELDS:
                box_rect = key_boxes[field_name]

                label_surface = font.render(field_name.capitalize(), True, TEXT_COLOR)
                screen.blit(label_surface, (50, box_rect.y + 8))

                draw_button(
                    screen,
                    font,
                    box_rect,
                    (
                        movement_keys[field_name].upper()
                        if movement_keys[field_name]
                        else "..."
                    ),
                    selected=selected_key_field == field_name,
                )

            hint_surface = small_font.render(
                "Click a direction, then press one keyboard key",
                True,
                MUTED_TEXT_COLOR,
            )
            screen.blit(hint_surface, (300, 308))

            draw_button(screen, font, setup_button, "Submit Setup")

        elif current_screen == "waiting":
            draw_card(screen, pygame.Rect(30, 20, WINDOW_WIDTH - 60, 510))

            title_surface = big_font.render("Waiting Room", True, ACCENT_COLOR)
            title_rect = title_surface.get_rect(center=(WINDOW_WIDTH // 2, 180))
            screen.blit(title_surface, title_rect)

            status_surface = font.render(status_message, True, TEXT_COLOR)
            status_rect = status_surface.get_rect(center=(WINDOW_WIDTH // 2, 250))
            screen.blit(status_surface, status_rect)

            design_surface = small_font.render(
                f"Design: {snake_design}",
                True,
                MUTED_TEXT_COLOR,
            )
            design_rect = design_surface.get_rect(center=(WINDOW_WIDTH // 2, 295))
            screen.blit(design_surface, design_rect)

        elif current_screen == "game":
            draw_game_view(
                screen,
                font,
                small_font,
                big_font,
                player_states,
                pie_positions,
                obstacle_positions,
                remaining_time,
                chat_messages,
                chat_input,
                typing_chat,
                countdown_text,
                game_over,
                winner_text,
                final_health_lines,
                spectator_mode,
                confetti_button_rects,
                confetti_bursts,
                return_to_lobby_button,
            )

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    client_socket.close()


if __name__ == "__main__":
    main()
