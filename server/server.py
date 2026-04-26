import random
import socket
import sys
import threading
import time

WINDOW_WIDTH = 760
WINDOW_HEIGHT = 500
PLAYER_SIZE = 20
MOVE_STEP = 20
GAME_TICK_SECONDS = 0.1
STARTING_HEALTH = 100
HEALTH_PENALTY = 10
MATCH_TIME_LIMIT = 60
COUNTDOWN_START = 3
OBSTACLE_ACTIVE_SECONDS = 3
OBSTACLE_INACTIVE_SECONDS = 2
PIE_COUNT = 3
STARTING_POSITIONS = [
    {"x": 100, "y": 100},
    {"x": 620, "y": 380},
    {"x": 100, "y": 380},
    {"x": 620, "y": 100},
]

usernames = []
clients = {}
selected_opponents = {}
confirmed_matches = {}
spectators = set()
snake_setups = {}
movement_commands = {}
player_positions = {}
player_bodies = {}
player_started_moving = {}
player_health = {}
client_buffers = {}
pie_positions = []
obstacle_positions = [
    (260, 160),
    (280, 160),
    (300, 160),
    (460, 320),
    (480, 320),
    (500, 320),
    (360, 240),
    (380, 240),
    (380, 260),
    (160, 260),
    (160, 280),
    (600, 200),
    (620, 200),
]
obstacle_active_states = [True for _ in obstacle_positions]
game_over = False
match_start_time = None
countdown_started = False
both_ready_sent = False
game_tick_started = False
lock = threading.Lock()


def send_message(client_socket, message):
    try:
        client_socket.sendall(f"{message}\n".encode())
    except Exception:
        pass


def extract_messages(buffer):
    messages = []

    while "\n" in buffer:
        message, buffer = buffer.split("\n", 1)
        if message != "":
            messages.append(message)

    return messages, buffer


def get_opposite_direction(direction):
    opposites = {
        "UP": "DOWN",
        "DOWN": "UP",
        "LEFT": "RIGHT",
        "RIGHT": "LEFT",
    }

    return opposites.get(direction)


def send_online_users():
    with lock:
        online_users = ",".join(usernames)
        message = f"ONLINE_USERS:{online_users}"
        client_sockets = list(clients.values())

    for client_socket in client_sockets:
        send_message(client_socket, message)


def get_active_match_text():
    if len(confirmed_matches) >= 2:
        players = sorted(confirmed_matches.keys())
        return f"{players[0]},{players[1]}"

    return None


def send_match_status():
    with lock:
        active_match_text = get_active_match_text()
        client_sockets = list(clients.values())

    if active_match_text is None:
        message = "NO_ACTIVE_MATCH"
    else:
        message = f"MATCH_ACTIVE:{active_match_text}"

    for client_socket in client_sockets:
        send_message(client_socket, message)


def broadcast_to_match_viewers(message):
    with lock:
        viewer_names = set(confirmed_matches.keys())
        viewer_names.update(spectators)
        viewer_sockets = []

        for viewer_name in viewer_names:
            viewer_socket = clients.get(viewer_name)

            if viewer_socket is not None:
                viewer_sockets.append(viewer_socket)

    for viewer_socket in viewer_sockets:
        send_message(viewer_socket, message)


def reset_player_for_match(username, start_index):
    start_position = STARTING_POSITIONS[start_index % len(STARTING_POSITIONS)]
    player_positions[username] = start_position.copy()
    player_bodies[username] = create_initial_body(start_position)
    player_started_moving[username] = False
    player_health[username] = STARTING_HEALTH
    movement_commands[username] = None


def confirm_match(player_one, player_two):
    global game_over
    global match_start_time
    global countdown_started
    global both_ready_sent

    with lock:
        game_over = False
        match_start_time = None
        countdown_started = False
        both_ready_sent = False

        confirmed_matches[player_one] = player_two
        confirmed_matches[player_two] = player_one
        spectators.clear()
        for index in range(len(obstacle_active_states)):
            obstacle_active_states[index] = True
        snake_setups.pop(player_one, None)
        snake_setups.pop(player_two, None)
        reset_player_for_match(player_one, 0)
        reset_player_for_match(player_two, 1)
        generate_all_pies()
        first_socket = clients.get(player_one)
        second_socket = clients.get(player_two)

    if first_socket is not None:
        send_message(first_socket, f"MATCH_CONFIRMED:{player_one}:{player_two}")

    if second_socket is not None:
        send_message(second_socket, f"MATCH_CONFIRMED:{player_one}:{player_two}")

    send_match_status()


def get_confirmed_players():
    with lock:
        return list(confirmed_matches.keys())


def send_countdown_message(countdown_value):
    confirmed_players = get_confirmed_players()
    send_game_state()

    for player in confirmed_players:
        with lock:
            player_socket = clients.get(player)

        if player_socket is not None:
            send_message(player_socket, f"COUNTDOWN:{countdown_value}")


def send_both_ready():
    confirmed_players = get_confirmed_players()
    send_game_state()

    for player in confirmed_players:
        with lock:
            player_socket = clients.get(player)

        if player_socket is not None:
            send_message(player_socket, "BOTH_READY")


def get_game_player_names():
    if len(confirmed_matches) >= 2:
        return set(confirmed_matches.keys())

    return set(player_bodies.keys())


def update_obstacle_active_states():
    if match_start_time is None or game_over:
        for index in range(len(obstacle_active_states)):
            obstacle_active_states[index] = True

        return

    cycle_seconds = OBSTACLE_ACTIVE_SECONDS + OBSTACLE_INACTIVE_SECONDS
    elapsed_seconds = time.time() - match_start_time
    active_now = elapsed_seconds % cycle_seconds < OBSTACLE_ACTIVE_SECONDS

    for index in range(len(obstacle_active_states)):
        obstacle_active_states[index] = active_now


def get_active_obstacle_positions():
    update_obstacle_active_states()
    active_positions = set()

    for index, position in enumerate(obstacle_positions):
        if obstacle_active_states[index]:
            active_positions.add(position)

    return active_positions


def send_game_state():
    with lock:
        update_obstacle_active_states()
        player_data = []
        game_player_names = get_game_player_names()

        for username in sorted(game_player_names):
            body = player_bodies.get(username, [])
            if not body:
                continue

            head_x, head_y = body[0]
            design = "green"

            if username in snake_setups:
                design = snake_setups[username]["design"]

            health = player_health.get(username, STARTING_HEALTH)
            body_data = "~".join(
                f"{segment_x}:{segment_y}" for segment_x, segment_y in body
            )
            player_data.append(
                f"{username},{head_x},{head_y},{design},{health},{body_data}"
            )

        obstacle_data = []
        for index, position in enumerate(obstacle_positions):
            obstacle_x, obstacle_y = position
            active_value = 1 if obstacle_active_states[index] else 0
            obstacle_data.append(f"{obstacle_x},{obstacle_y},{active_value}")

        remaining_time = MATCH_TIME_LIMIT
        if match_start_time is not None:
            elapsed_time = int(time.time() - match_start_time)
            remaining_time = MATCH_TIME_LIMIT - elapsed_time
            if remaining_time < 0:
                remaining_time = 0

        pie_data = ";".join(f"{pie_x},{pie_y}" for pie_x, pie_y in pie_positions)

        message = (
            f"GAME_STATE:{';'.join(player_data)}|"
            f"{pie_data}|"
            f"{';'.join(obstacle_data)}|"
            f"{remaining_time}"
        )
        client_sockets = list(clients.values())

    for client_socket in client_sockets:
        send_message(client_socket, message)


def send_game_over(result_text):
    with lock:
        health_data = []

        for username in sorted(get_game_player_names()):
            health_data.append(f"{username},{player_health[username]}")

        message = f"GAME_OVER:{result_text}|{';'.join(health_data)}"
        client_sockets = list(clients.values())

    for client_socket in client_sockets:
        send_message(client_socket, message)


def get_all_snake_segments():
    segments = set()
    game_player_names = get_game_player_names()

    for username in game_player_names:
        body = player_bodies.get(username, [])
        for segment in body:
            segments.add(segment)

    return segments


def get_blocked_pie_positions(skip_pie_index=None):
    blocked_positions = set(obstacle_positions)
    blocked_positions.update(get_all_snake_segments())

    for index, pie_position in enumerate(pie_positions):
        if skip_pie_index is None or index != skip_pie_index:
            blocked_positions.add(pie_position)

    return blocked_positions


def get_available_pie_positions(skip_pie_index=None):
    blocked_positions = get_blocked_pie_positions(skip_pie_index)
    available_positions = []

    for x in range(0, WINDOW_WIDTH, MOVE_STEP):
        for y in range(0, WINDOW_HEIGHT, MOVE_STEP):
            position = (x, y)

            if position not in blocked_positions:
                available_positions.append(position)

    return available_positions


def generate_all_pies():
    pie_positions.clear()

    for _ in range(PIE_COUNT):
        available_positions = get_available_pie_positions()

        if not available_positions:
            return

        pie_positions.append(random.choice(available_positions))


def respawn_pie(pie_index):
    available_positions = get_available_pie_positions(pie_index)

    if not available_positions:
        del pie_positions[pie_index]
        return

    pie_positions[pie_index] = random.choice(available_positions)


def create_initial_body(start_position):
    head_x = start_position["x"]
    head_y = start_position["y"]
    body = []

    for index in range(4):
        segment_x = head_x - (index * MOVE_STEP)

        if segment_x < 0:
            segment_x = head_x + (index * MOVE_STEP)

        body.append((segment_x, head_y))

    return body


def create_body_after_first_move(old_x, old_y, new_x, new_y, direction, length):
    body = [(new_x, new_y), (old_x, old_y)]

    for index in range(1, length - 1):
        if direction == "UP":
            body.append((old_x, old_y + (index * MOVE_STEP)))
        elif direction == "DOWN":
            body.append((old_x, old_y - (index * MOVE_STEP)))
        elif direction == "LEFT":
            body.append((old_x + (index * MOVE_STEP), old_y))
        elif direction == "RIGHT":
            body.append((old_x - (index * MOVE_STEP), old_y))

    return body


def move_player(username, direction):
    global game_over

    winner = None

    if (
        username not in player_bodies
        or direction not in ["UP", "DOWN", "LEFT", "RIGHT"]
    ):
        return winner

    old_body = player_bodies[username]
    if not old_body:
        return winner

    old_x, old_y = old_body[0]
    new_x = old_x
    new_y = old_y
    blocked_move = False

    if direction == "UP":
        new_y -= MOVE_STEP
    elif direction == "DOWN":
        new_y += MOVE_STEP
    elif direction == "LEFT":
        new_x -= MOVE_STEP
    elif direction == "RIGHT":
        new_x += MOVE_STEP

    if new_x < 0 or new_x > WINDOW_WIDTH - PLAYER_SIZE:
        player_health[username] -= HEALTH_PENALTY
        blocked_move = True

    if new_y < 0 or new_y > WINDOW_HEIGHT - PLAYER_SIZE:
        player_health[username] -= HEALTH_PENALTY
        blocked_move = True

    if (new_x, new_y) in get_active_obstacle_positions():
        player_health[username] -= HEALTH_PENALTY
        blocked_move = True

    for other_username in get_game_player_names():
        if other_username != username:
            other_body = player_bodies.get(other_username, [])

            if (new_x, new_y) in other_body:
                player_health[username] -= HEALTH_PENALTY
                blocked_move = True
                break

    if (
        player_started_moving.get(username, False)
        and (new_x, new_y) in old_body[1:]
    ):
        player_health[username] -= HEALTH_PENALTY
        blocked_move = True

    if player_health[username] < 0:
        player_health[username] = 0

    if not blocked_move:
        eaten_pie_index = None

        for index, pie_position in enumerate(pie_positions):
            if (new_x, new_y) == pie_position:
                eaten_pie_index = index
                break

        ate_pie = eaten_pie_index is not None
        if not player_started_moving.get(username, False):
            new_length = len(old_body)
            if ate_pie:
                new_length += 1

            new_body = create_body_after_first_move(
                old_x,
                old_y,
                new_x,
                new_y,
                direction,
                new_length,
            )
            player_started_moving[username] = True
        else:
            new_body = [(new_x, new_y)] + old_body

        if not ate_pie and len(new_body) > len(old_body):
            new_body.pop()

        player_bodies[username] = new_body
        player_positions[username]["x"] = new_x
        player_positions[username]["y"] = new_y

        if ate_pie:
            player_health[username] += 10
            respawn_pie(eaten_pie_index)

    if player_health[username] == 0:
        game_over = True

        for other_username in get_game_player_names():
            if other_username != username:
                winner = other_username
                break

    return winner


def run_countdown():
    global match_start_time

    for countdown_value in range(COUNTDOWN_START, 0, -1):
        with lock:
            if len(confirmed_matches) != 2:
                return

        send_countdown_message(countdown_value)
        time.sleep(1)

    with lock:
        if len(confirmed_matches) != 2:
            return

        match_start_time = time.time()

    send_countdown_message("GO")


def run_game_tick():
    while True:
        winner = None
        should_send_state = False

        with lock:
            if (
                not game_over
                and match_start_time is not None
                and len(confirmed_matches) == 2
            ):
                should_send_state = True
                confirmed_players = list(confirmed_matches.keys())

                for username in confirmed_players:
                    direction = movement_commands.get(username)

                    if direction is not None:
                        winner = move_player(username, direction)

                        if winner is not None:
                            break

        if should_send_state:
            send_game_state()

            if winner is not None:
                send_game_over(winner)
            else:
                time_winner = check_time_limit()

                if time_winner is not None:
                    send_game_state()
                    send_game_over(time_winner)

        time.sleep(GAME_TICK_SECONDS)


def start_game_tick_thread():
    global game_tick_started

    with lock:
        if game_tick_started:
            return

        game_tick_started = True

    game_tick_thread = threading.Thread(target=run_game_tick, daemon=True)
    game_tick_thread.start()


def maybe_start_countdown():
    global countdown_started
    global both_ready_sent

    with lock:
        if countdown_started:
            return

        confirmed_players = list(confirmed_matches.keys())
        if len(confirmed_players) != 2:
            return

        for player in confirmed_players:
            if player not in snake_setups:
                return

        countdown_started = True
        both_ready_sent = True

    send_both_ready()
    countdown_thread = threading.Thread(target=run_countdown, daemon=True)
    countdown_thread.start()


def get_chat_target(username):
    with lock:
        if username in confirmed_matches:
            return confirmed_matches[username]

    return None


def check_time_limit():
    global game_over

    with lock:
        if game_over or match_start_time is None:
            return None

        elapsed_time = int(time.time() - match_start_time)
        if elapsed_time < MATCH_TIME_LIMIT:
            return None

        game_over = True

        confirmed_players = list(confirmed_matches.keys())

        if len(confirmed_players) < 2:
            return "DRAW"

        first_player = confirmed_players[0]
        second_player = confirmed_players[1]
        first_health = player_health[first_player]
        second_health = player_health[second_player]

        if first_health > second_health:
            return first_player
        if second_health > first_health:
            return second_player

        return "DRAW"


def handle_client_message(client_socket, username, message):
    global game_over
    global match_start_time
    global countdown_started
    global both_ready_sent

    if message.startswith("SNAKE_SETUP:"):
        setup_data = message[len("SNAKE_SETUP:"):]
        parts = setup_data.split("|")

        if len(parts) != 5:
            reply = "INVALID_SNAKE_SETUP"
        else:
            snake_design, up_key, down_key, left_key, right_key = parts

            if (
                snake_design == ""
                or len(up_key) != 1
                or len(down_key) != 1
                or len(left_key) != 1
                or len(right_key) != 1
                or len({up_key, down_key, left_key, right_key}) != 4
            ):
                reply = "INVALID_SNAKE_SETUP"
            else:
                with lock:
                    snake_setups[username] = {
                        "design": snake_design,
                        "up": up_key,
                        "down": down_key,
                        "left": left_key,
                        "right": right_key,
                    }

                reply = "SNAKE_SETUP_ACCEPTED"

        send_message(client_socket, reply)

        if reply == "SNAKE_SETUP_ACCEPTED":
            send_game_state()
            maybe_start_countdown()

    elif message.startswith("DIRECTION:"):
        command = message[len("DIRECTION:"):]

        if command in ["UP", "DOWN", "LEFT", "RIGHT"]:
            accepted_direction = False

            with lock:
                if not game_over and username in confirmed_matches:
                    current_direction = movement_commands.get(username)

                    if command != get_opposite_direction(current_direction):
                        movement_commands[username] = command
                        accepted_direction = True

            if accepted_direction:
                print(f"{username} set direction to {command}")

    elif message.startswith("SELECT_OPPONENT:"):
        opponent = message[len("SELECT_OPPONENT:"):]
        should_confirm = False

        with lock:
            if len(confirmed_matches) >= 2:
                reply = "Match already active"
            elif opponent == username:
                reply = "Invalid opponent"
            elif opponent not in usernames:
                reply = "Opponent not available"
            else:
                selected_opponents[username] = opponent
                reply = f"MATCH_PENDING:{opponent}"

                if selected_opponents.get(opponent) == username:
                    should_confirm = True

        send_message(client_socket, reply)

        if should_confirm:
            players = sorted([username, opponent])
            confirm_match(players[0], players[1])

    elif message.startswith("CHAT:"):
        chat_message = message[len("CHAT:"):]
        target_username = get_chat_target(username)

        if chat_message.strip() != "" and target_username is not None:
            with lock:
                target_socket = clients.get(target_username)

            if target_socket is not None:
                send_message(target_socket, f"CHAT_FROM:{username}:{chat_message}")

    elif message == "SPECTATE":
        with lock:
            active_match_text = get_active_match_text()
            is_player = username in confirmed_matches

        if is_player:
            send_message(client_socket, "ALREADY_PLAYING")
        elif active_match_text is None:
            send_message(client_socket, "NO_ACTIVE_MATCH")
        else:
            with lock:
                spectators.add(username)

            send_message(client_socket, "SPECTATE_ACCEPTED")
            send_game_state()

    elif message.startswith("CHEER_CONFETTI:"):
        target_username = message[len("CHEER_CONFETTI:"):]
        should_broadcast = False

        with lock:
            if (
                len(confirmed_matches) >= 2
                and not game_over
                and username in spectators
                and username not in confirmed_matches
                and target_username in confirmed_matches
            ):
                should_broadcast = True

        if should_broadcast:
            broadcast_to_match_viewers(f"ARENA_CONFETTI:{target_username}")

    elif message == "RETURN_TO_LOBBY":
        match_was_cleared = False

        with lock:
            spectators.discard(username)

            if username in selected_opponents:
                del selected_opponents[username]

            users_to_clear = []
            for player, opponent_name in selected_opponents.items():
                if opponent_name == username:
                    users_to_clear.append(player)

            for player in users_to_clear:
                del selected_opponents[player]

            if username in confirmed_matches:
                opponent = confirmed_matches[username]
                del confirmed_matches[username]
                match_was_cleared = True

                if opponent in confirmed_matches:
                    del confirmed_matches[opponent]

            if username in snake_setups:
                del snake_setups[username]

            movement_commands[username] = None
            player_started_moving[username] = False

            if len(confirmed_matches) < 2:
                match_start_time = None
                countdown_started = False
                both_ready_sent = False
                game_over = False
                spectators.clear()

        if match_was_cleared:
            send_match_status()


def handle_client(client_socket, username):
    global game_over
    global match_start_time
    global countdown_started
    global both_ready_sent

    client_socket.settimeout(0.1)

    try:
        while True:
            time_winner = check_time_limit()
            if time_winner is not None:
                send_game_state()
                send_game_over(time_winner)
                continue

            try:
                data = client_socket.recv(1024).decode()
            except socket.timeout:
                continue

            if not data:
                break

            with lock:
                buffer = client_buffers.get(username, "") + data
                messages, buffer = extract_messages(buffer)
                client_buffers[username] = buffer

            for message in messages:
                handle_client_message(client_socket, username, message)
    except Exception:
        pass
    finally:
        match_was_cleared = False

        with lock:
            if username in usernames:
                usernames.remove(username)
            if username in clients:
                del clients[username]
            if username in client_buffers:
                del client_buffers[username]
            spectators.discard(username)
            if username in selected_opponents:
                del selected_opponents[username]
            if username in confirmed_matches:
                opponent = confirmed_matches[username]
                del confirmed_matches[username]
                match_was_cleared = True
                if opponent in confirmed_matches:
                    del confirmed_matches[opponent]
            if username in snake_setups:
                del snake_setups[username]
            if username in movement_commands:
                del movement_commands[username]
            if username in player_positions:
                del player_positions[username]
            if username in player_bodies:
                del player_bodies[username]
            if username in player_started_moving:
                del player_started_moving[username]
            if username in player_health:
                del player_health[username]

            users_to_clear = []
            for player, opponent in selected_opponents.items():
                if opponent == username:
                    users_to_clear.append(player)

            for player in users_to_clear:
                del selected_opponents[player]

            if len(confirmed_matches) < 2:
                match_start_time = None
                countdown_started = False
                both_ready_sent = False
                game_over = False
                spectators.clear()

        print(f"{username} disconnected")
        client_socket.close()
        send_online_users()
        if match_was_cleared:
            send_match_status()
        send_game_state()


def main():
    start_game_tick_thread()

    if len(sys.argv) != 2:
        print("Usage: python run_server.py <port>")
        return

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be an integer")
        return

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen()

        print(f"Server is listening on port {port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Client connected from {client_address}")
            client_socket.settimeout(0.1)

            username_buffer = ""
            username = None

            while username is None:
                messages, username_buffer = extract_messages(username_buffer)

                if not messages:
                    try:
                        data = client_socket.recv(1024).decode()
                    except socket.timeout:
                        continue

                    if not data:
                        client_socket.close()
                        break

                    username_buffer += data
                    messages, username_buffer = extract_messages(username_buffer)

                for message in messages:
                    requested_username = message.strip()

                    if requested_username == "":
                        send_message(client_socket, "Invalid username")
                    else:
                        with lock:
                            username_taken = (
                                requested_username.lower()
                                in [name.lower() for name in usernames]
                            )

                        if username_taken:
                            send_message(client_socket, "Username already in use")
                        else:
                            username = requested_username
                            break

            if username is None:
                continue

            print(f"Username received: {username}")

            with lock:
                start_index = len(usernames) % len(STARTING_POSITIONS)

                usernames.append(username)
                clients[username] = client_socket
                client_buffers[username] = username_buffer
                player_positions[username] = STARTING_POSITIONS[start_index].copy()
                player_bodies[username] = create_initial_body(
                    STARTING_POSITIONS[start_index]
                )
                player_started_moving[username] = False
                player_health[username] = STARTING_HEALTH
                movement_commands[username] = None

            send_message(client_socket, "Username accepted")
            print(f"{username} joined the server")
            send_online_users()
            send_match_status()

            client_thread = threading.Thread(
                target=handle_client,
                args=(client_socket, username),
                daemon=True,
            )
            client_thread.start()

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()


if __name__ == "__main__":
    main()
