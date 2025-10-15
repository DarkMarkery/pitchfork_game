import asyncio
import pygame
import sys
import os

async def main():
    pygame.init()

    # --- Config ---
    FPS = 60
    PLAYER_SPEED = 4

    # --- Detect iPad/Tablet ---
    info = pygame.display.Info()
    screen_width, screen_height = info.current_w, info.current_h
    
    # iPad detection based on common iPad resolutions and aspect ratios
    is_ipad = False
    ipad_resolutions = [
        (1024, 768), (1024, 1366), (1366, 1024),  # iPad Mini, iPad Pro
        (768, 1024), (834, 1194), (1194, 834),    # iPad Air, iPad Pro
        (810, 1080), (1080, 810),                 # iPad 10th gen
        (744, 1133), (1133, 744)                  # iPad Pro 11"
    ]
    
    # Check if current resolution matches common iPad resolutions
    for w, h in ipad_resolutions:
        if (abs(screen_width - w) <= 10 and abs(screen_height - h) <= 10) or \
           (abs(screen_width - h) <= 10 and abs(screen_height - w) <= 10):
            is_ipad = True
            break
    
    # Also check by aspect ratio (common iPad aspect ratios)
    aspect_ratio = screen_width / screen_height
    ipad_aspects = [4/3, 3/4, 0.75, 1.333]
    for ipad_aspect in ipad_aspects:
        if abs(aspect_ratio - ipad_aspect) < 0.1:
            is_ipad = True
            break

    # --- Web-Compatible Setup ---
    if is_ipad:
        # Use full screen for iPad
        WIDTH, HEIGHT = screen_width, screen_height
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        print(f"iPad mode detected: {WIDTH}x{HEIGHT}")
    else:
        WIDTH, HEIGHT = 1200, 800
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    
    pygame.display.set_caption("Pitchfork Path")
    clock = pygame.time.Clock()

    # --- iPad-Specific Settings ---
    if is_ipad:
        # Adjust speeds and sizes for touch interface
        PLAYER_SPEED = 6  # Slightly faster for larger screen
        SCALE = 2.5       # Larger tiles for iPad
        FONT_SCALE = 1.3  # Larger text for iPad
        TOUCH_CONTROLS = True
    else:
        SCALE = 2
        FONT_SCALE = 1.0
        TOUCH_CONTROLS = False

    # --- Debug ---
    DEBUG_INTERACTION = False
    DEBUG_COLLISION = False

    # --- Tile Scaling ---
    BASE_TILE_SIZE = 64
    TILE_SIZE = BASE_TILE_SIZE * SCALE

    # --- Base Fork Layout ---
    fork_base = [
        [58, "PATH", 58, "PATH", 58, "PATH", 58],
        [58, "PATH", 58, "PATH", 58, "PATH", 58],
        [58, "PATH", 58, "PATH", 58, "PATH", 58],
        [58, "TWENRIGHT", 20, "TWENONELEFT", 20, "TWENONELEFTTWO", 58],
        [58, 23, 2, 2, 2, "LEFT_PATH", 2, 2, 2, 24],
        [58, 58, 58, 58, 58, "PATH", 58, 58, 58],
        [58, 58, 58, 58, 58, "DOWNPATH", 58, 58, 58],
    ]

    # Expand placeholders
    fork_map = []
    for row in fork_base:
        expanded = []
        for cell in row:
            if cell == "PATH":
                expanded.extend([12, 14, 10])
            elif cell == "LEFT_PATH":
                expanded.extend([3, 14, 1])
            elif cell == "TWENRIGHT":
                expanded.extend([12, 14, 19])
            elif cell == "TWENONELEFT":
                expanded.extend([21, 14, 19])
            elif cell == "TWENONELEFTTWO":
                expanded.extend([21, 14, 10])
            elif cell == "DOWNPATH":
                expanded.extend([23, 2, 22])
            else:
                expanded.append(cell)
        fork_map.append(expanded)

    max_cols = max(len(row) for row in fork_map)
    for row in fork_map:
        while len(row) < max_cols:
            row.append(58)

    fork_rows = len(fork_map)
    fork_cols = len(fork_map[0])
    fork_width = fork_cols * TILE_SIZE
    fork_height = fork_rows * TILE_SIZE
    offset_x = (WIDTH - fork_width) // 2
    offset_y = (HEIGHT - fork_height) // 2

    # --- Path Color Detection ---
    def is_path_color(color):
        r, g, b = color[:3]
        if g > r + 20 and g > b + 20 and g > 100:
            return False
        if r > 80 and g > 60 and b < 80 and abs(r - g) < 40:
            return True
        if abs(r - g) < 20 and abs(g - b) < 20 and r > 50 and r < 180:
            return True
        return True

    # --- Load Tiles ---
    tiles = {}
    for i in range(1, 59):
        filename = f"tiles/tile{i}.png"
        if os.path.exists(filename):
            img = pygame.image.load(filename).convert_alpha()
            img = pygame.transform.scale(img, (TILE_SIZE, TILE_SIZE))
            tiles[i] = img

    def is_walkable_pixel(x, y):
        tile_x = (x - offset_x) // TILE_SIZE
        tile_y = (y - offset_y) // TILE_SIZE
        
        if not (0 <= tile_y < fork_rows and 0 <= tile_x < fork_cols):
            return False
        
        tile_num = fork_map[tile_y][tile_x]
        if tile_num not in tiles:
            return False
        
        pixel_x = (x - offset_x) % TILE_SIZE
        pixel_y = (y - offset_y) % TILE_SIZE
        
        if not (0 <= pixel_x < TILE_SIZE and 0 <= pixel_y < TILE_SIZE):
            return False
        
        try:
            color = tiles[tile_num].get_at((pixel_x, pixel_y))
            return is_path_color(color)
        except IndexError:
            return False

    def can_move_pixel(rect):
        sample_points = [
            (rect.centerx, rect.centery),
            (rect.left, rect.top),
            (rect.right - 1, rect.top),
            (rect.left, rect.bottom - 1),
            (rect.right - 1, rect.bottom - 1),
            (rect.centerx, rect.top),
            (rect.centerx, rect.bottom - 1),
            (rect.left, rect.centery),
            (rect.right - 1, rect.centery),
        ]
        
        for x, y in sample_points:
            if not is_walkable_pixel(x, y):
                return False
        return True

    # --- Character Class ---
    def load_spritesheet(filename, frame_width, frame_height, scale=1.5):
        if not os.path.exists(filename):
            return [[]]
        sheet = pygame.image.load(filename).convert_alpha()
        sheet_rect = sheet.get_rect()
        rows = sheet_rect.height // frame_height
        cols = sheet_rect.width // frame_width
        frames = []
        for r in range(rows):
            row_frames = []
            for c in range(cols):
                frame_rect = pygame.Rect(c * frame_width, r * frame_height, frame_width, frame_height)
                frame = sheet.subsurface(frame_rect).copy()
                if not pygame.mask.from_surface(frame).count():
                    continue
                frame = pygame.transform.scale(frame, (int(frame_width * scale), int(frame_height * scale)))
                row_frames.append(frame)
            frames.append(row_frames)
        return frames

    class Character:
        def __init__(self, idle_sheet, run_sheet, frame_size, pos, scale=1.5):
            self.scale = scale
            self.idle_frames = load_spritesheet(idle_sheet, *frame_size, scale)
            self.run_frames = load_spritesheet(run_sheet, *frame_size, scale)
            self.frame_width, self.frame_height = int(frame_size[0] * scale), int(frame_size[1] * scale)
            self.sprite_rect = pygame.Rect(pos[0], pos[1], self.frame_width, self.frame_height)
            
            hitbox_width = int(self.frame_width * 0.4)
            hitbox_height = int(self.frame_height * 0.2)
            hitbox_x = pos[0] + (self.frame_width - hitbox_width) // 2
            hitbox_y = pos[1] + (self.frame_height - hitbox_height)
            self.rect = pygame.Rect(hitbox_x, hitbox_y, hitbox_width, hitbox_height)
            
            self.direction = 0
            self.anim_timer = 0
            self.frame_index = 0
            self.state = "idle"
            
            frames = self.get_frames()
            if frames and frames[0]:
                self.image = frames[0]
            else:
                self.image = pygame.Surface((self.frame_width, self.frame_height), pygame.SRCALPHA)
                self.image.fill((255, 0, 0, 150))

        def update(self, dt, moving, direction):
            if moving:
                self.state = "run"
                self.direction = direction
            else:
                self.state = "idle"
                
            speed = 100 if self.state == "run" else 200
            self.anim_timer += dt
            if self.anim_timer >= speed:
                self.anim_timer = 0
                self.frame_index += 1
                
            frames = self.get_frames()
            if not frames:
                return
                
            idx = max(0, min(self.direction, len(frames) - 1))
            anim_frames = frames[idx] if frames[idx] else frames[0]
            if not anim_frames:
                return
            
            # Special handling for up direction with only 4 frames
            if self.state == "idle" and self.direction == 3 and len(anim_frames) == 4:
                if self.frame_index >= len(anim_frames):
                    self.frame_index = 0
            else:
                if self.frame_index >= len(anim_frames):
                    self.frame_index = 0
            
            self.image = anim_frames[self.frame_index]
            self.sprite_rect.midbottom = self.rect.midbottom

        def get_frames(self):
            return self.run_frames if self.state == "run" else self.idle_frames

        def draw(self, surface):
            surface.blit(self.image, self.sprite_rect.topleft)

    # --- Player Setup ---
    FRAME_SIZE = (64, 64)
    start_row, start_col = None, None
    for r in range(fork_rows - 1, -1, -1):
        for c in range(fork_cols):
            if fork_map[r][c] == 14:
                start_row, start_col = r, c
                break
        if start_row is not None:
            break

    def get_tile_center(row, col):
        return (offset_x + col * TILE_SIZE + TILE_SIZE // 2, offset_y + row * TILE_SIZE + TILE_SIZE // 2)

    if start_row is None:
        start_row, start_col = fork_rows - 1, fork_cols // 2

    start_x, start_y = get_tile_center(start_row, start_col)
    character = Character(
        "Unarmed_Idle_without_shadow.png", 
        "Unarmed_Run_without_shadow.png", 
        FRAME_SIZE, 
        (start_x - FRAME_SIZE[0] // 2, start_y - FRAME_SIZE[1] // 2), 
        scale=3 if not is_ipad else 3.5  # Larger character on iPad
    )

    # --- Buildings ---
    building_images = {}
    building_names = ["cathedral", "mosque", "synagogue"]
    for name in building_names:
        path = f"{name}.png"
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            if name == "mosque":
                img = pygame.transform.scale(img, (int(TILE_SIZE * 1.7), int(TILE_SIZE * 1.7)))
            elif name == "synagogue":
                img = pygame.transform.scale(img, (int(TILE_SIZE * 1.6), int(TILE_SIZE * 1.8)))
            else:
                img = pygame.transform.scale(img, (int(TILE_SIZE * 1.5), int(TILE_SIZE * 1.7)))
            building_images[name] = img

    # --- Building placement ---
    top_row = None
    path_cols = []
    for r in range(fork_rows):
        for c in range(fork_cols):
            if fork_map[r][c] == 14:
                if top_row is None:
                    top_row = r
                if r == top_row:
                    path_cols.append(c)
        if top_row is not None:
            break

    path_cols.sort()
    buildings = []
    building_colliders = []

    if len(path_cols) >= 3:
        center_y = offset_y + top_row * TILE_SIZE + TILE_SIZE // 2
        positions = [
            (offset_x + path_cols[0] * TILE_SIZE + TILE_SIZE // 2, center_y),
            (offset_x + path_cols[len(path_cols)//2] * TILE_SIZE + TILE_SIZE // 2, center_y),
            (offset_x + path_cols[-1] * TILE_SIZE + TILE_SIZE // 2, center_y),
        ]
        
        for (name, pos) in zip(building_names, positions):
            if name in building_images:
                img = building_images[name]
                y_offset = TILE_SIZE * 1.5
                rect = img.get_rect(midbottom=(pos[0], pos[1] + y_offset))
                buildings.append((name, img, rect))
                
                collider_height = rect.height // 4
                collider_rect = pygame.Rect(
                    rect.centerx - rect.width // 4, 
                    rect.bottom - collider_height, 
                    rect.width // 2, 
                    collider_height
                )
                building_colliders.append((name, collider_rect))

    # --- NPCs ---
    npc_data = []
    npc_images = {}
    npc_dialogues = {
        "cathedral": [
            "Bonjour ! Je suis chrétien.", 
            "Chaque matin, je viens prier.", 
            "J'aime chanter à la chorale.", 
            "Ensuite, l'après-midi, je vais au marché et je joue aux jeux vidéos"
        ],
        "mosque": [
            "Salam ! Je suis musulman.", 
            "Je viens ici cinq fois par jour.", 
            "Après la prière, je partage le thé.", 
            "Ensuite, l'après-midi, je joue aux jeux vidéos et je vais à la piscine."
        ],
        "synagogue": [
            "Shalom ! Je suis juif.", 
            "J'étudie la Torah ici chaque matin.", 
            "Le samedi, je célèbre le Shabbat.", 
            "Ensuite, l'après-midi, je vais à la piscine et je vais au marché."
        ]
    }

    npc_files = {"cathedral": "priest.png", "mosque": "muslim.png", "synagogue": "rabbi.png"}
    for name, filename in npc_files.items():
        if os.path.exists(filename):
            img = pygame.image.load(filename).convert_alpha()
            img = pygame.transform.scale(img, (int(TILE_SIZE * 0.5), int(TILE_SIZE * 1.15)))
            npc_images[name] = img

    for (name, _, rect) in buildings:
        if name in npc_images:
            img = npc_images[name]
            npc_x = rect.centerx - img.get_width() // 2
            npc_y = rect.bottom - int(TILE_SIZE * 0.15)
            npc_rect = pygame.Rect(npc_x, npc_y, img.get_width(), img.get_height())
            
            dialogue_hitbox = pygame.Rect(
                npc_rect.centerx - TILE_SIZE, 
                npc_rect.bottom - TILE_SIZE // 2, 
                TILE_SIZE * 2, 
                TILE_SIZE
            )
            npc_data.append((name, img, npc_rect, dialogue_hitbox))

    # --- Touch Controls for iPad ---
    touch_controls = []
    if TOUCH_CONTROLS:
        # Create virtual D-pad
        control_size = TILE_SIZE * 1.2
        padding = TILE_SIZE // 2
        
        # Left side D-pad
        up_rect = pygame.Rect(padding, HEIGHT - control_size * 3 - padding, control_size, control_size)
        left_rect = pygame.Rect(padding - control_size, HEIGHT - control_size * 2 - padding, control_size, control_size)
        down_rect = pygame.Rect(padding, HEIGHT - control_size * 2 - padding, control_size, control_size)
        right_rect = pygame.Rect(padding + control_size, HEIGHT - control_size * 2 - padding, control_size, control_size)
        
        touch_controls = [
            ("up", up_rect, pygame.K_w),
            ("left", left_rect, pygame.K_a),
            ("down", down_rect, pygame.K_s),
            ("right", right_rect, pygame.K_d)
        ]
        
        # Action button (space equivalent)
        action_rect = pygame.Rect(WIDTH - control_size - padding, HEIGHT - control_size - padding, control_size, control_size)
        touch_controls.append(("action", action_rect, pygame.K_SPACE))

    # --- Dialogue State ---
    active_dialogue = None
    dialogue_lines = []
    dialogue_index = 0
    active_npc = None

    # --- Interaction Indicator ---
    interaction_font = pygame.font.SysFont(None, int(30 * FONT_SCALE))
    interaction_text = interaction_font.render("Appuyez sur ESPACE pour parler", True, (255, 255, 255))
    if TOUCH_CONTROLS:
        interaction_text = interaction_font.render("Touchez pour parler", True, (255, 255, 255))
    
    interaction_indicator_visible = False
    current_npc = None

    # --- Journal System ---
    talked_to = set()
    show_journal = False
    journal_text = [
        "Après avoir parlé aux trois fidèles des différentes religions canoniques,",
        "Tu réalises que, malgré leurs différences, ils partagent les même passions et les même passe-temps.",
        "Respect, paix et compréhension - voilà ton véritable chemin."
    ]

    # --- Draw Functions ---
    def draw_tilemap(surface, fork_map, tiles, offset_x, offset_y):
        rows = len(fork_map)
        cols = len(fork_map[0])
        
        if 58 in tiles:
            grass_tile = tiles[58]
            for y in range(0, HEIGHT, TILE_SIZE):
                for x in range(0, WIDTH, TILE_SIZE):
                    surface.blit(grass_tile, (x, y))
        
        for row in range(rows):
            for col in range(cols):
                tile_num = fork_map[row][col]
                if tile_num in tiles:
                    x = offset_x + col * TILE_SIZE
                    y = offset_y + row * TILE_SIZE
                    surface.blit(tiles[tile_num], (x, y))

    def collides_with_building(rect):
        for _, collider in building_colliders:
            if rect.colliderect(collider):
                return True
        return False

    def wrap_text(text, font, max_width):
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            test_width = font.size(test_line)[0]
            
            if test_width <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return lines

    def draw_dialogue_box(text, npc_rect):
        font = pygame.font.SysFont(None, int(30 * FONT_SCALE))
        
        max_box_width = int(WIDTH * 0.5)
        padding = 20
        
        lines = wrap_text(text, font, max_box_width - padding * 2)
        
        line_height = font.get_linesize()
        box_height = padding * 2 + line_height * len(lines)
        box_width = max_box_width
        
        box_x = npc_rect.centerx - box_width // 2
        box_y = npc_rect.top - box_height - 20
        
        if box_x < 10:
            box_x = 10
        if box_x + box_width > WIDTH - 10:
            box_x = WIDTH - box_width - 10
        if box_y < 10:
            box_y = 10
        
        s = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        screen.blit(s, (box_x, box_y))
        pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 2)
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, (255, 255, 255))
            screen.blit(text_surface, (box_x + padding, box_y + padding + i * line_height))

    def draw_journal_box(text):
        font = pygame.font.SysFont(None, int(36 * FONT_SCALE))
        lines = []
        words = text.split()
        line = ""
        
        for word in words:
            test_line = f"{line} {word}".strip()
            if font.size(test_line)[0] > WIDTH * 0.7:
                lines.append(line)
                line = word
            else:
                line = test_line
        if line:
            lines.append(line)
        
        box_width = int(WIDTH * 0.75)
        box_height = int(100 + 45 * len(lines))
        box_x = (WIDTH - box_width) // 2
        box_y = (HEIGHT - box_height) // 2
        
        s = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        screen.blit(s, (box_x, box_y))
        pygame.draw.rect(screen, (255, 255, 255), (box_x, box_y, box_width, box_height), 3)
        
        for i, line in enumerate(lines):
            txt = font.render(line, True, (255, 255, 255))
            screen.blit(txt, (box_x + 30, box_y + 40 + i * 45))

    def draw_interaction_indicator(npc_rect):
        indicator_x = npc_rect.centerx - interaction_text.get_width() // 2
        indicator_y = npc_rect.top - 40
        
        bg_rect = pygame.Rect(
            indicator_x - 10, 
            indicator_y - 5, 
            interaction_text.get_width() + 20, 
            interaction_text.get_height() + 10
        )
        bg_surface = pygame.Surface((bg_rect.width, bg_rect.height), pygame.SRCALPHA)
        bg_surface.fill((0, 0, 0, 180))
        screen.blit(bg_surface, bg_rect.topleft)
        
        screen.blit(interaction_text, (indicator_x, indicator_y))

    def draw_touch_controls():
        for name, rect, key in touch_controls:
            # Draw semi-transparent circle for each control
            s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            pygame.draw.circle(s, (100, 100, 100, 150), (rect.width//2, rect.height//2), rect.width//2)
            screen.blit(s, rect.topleft)
            
            # Draw direction arrows or action symbol
            font = pygame.font.SysFont(None, int(40 * FONT_SCALE))
            if name == "up":
                text = font.render("↑", True, (255, 255, 255))
            elif name == "left":
                text = font.render("←", True, (255, 255, 255))
            elif name == "down":
                text = font.render("↓", True, (255, 255, 255))
            elif name == "right":
                text = font.render("→", True, (255, 255, 255))
            else:  # action
                text = font.render("⚡", True, (255, 255, 255))
            
            text_rect = text.get_rect(center=rect.center)
            screen.blit(text, text_rect)

    # --- Touch Input Handling ---
    def handle_touch_input():
        keys_pressed = set()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, keys_pressed
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False, keys_pressed
                keys_pressed.add(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and TOUCH_CONTROLS:
                pos = pygame.mouse.get_pos()
                for name, rect, key in touch_controls:
                    if rect.collidepoint(pos):
                        keys_pressed.add(key)
                        break
                # Also check if tapping near an NPC for interaction
                if not active_dialogue:
                    for name, img, npc_rect, dialogue_hitbox in npc_data:
                        if dialogue_hitbox.collidepoint(pos):
                            keys_pressed.add(pygame.K_SPACE)
                            break
        
        return True, keys_pressed

    # --- Main Game Loop ---
    running = True
    while running:
        dt = clock.tick(FPS)
        
        # Handle input (keyboard + touch)
        running, keys_pressed = handle_touch_input()
        if not running:
            break

        # Check for specific key events in the pressed keys
        if pygame.K_ESCAPE in keys_pressed:
            running = False
            
        if pygame.K_c in keys_pressed:
            DEBUG_COLLISION = not DEBUG_COLLISION
            
        if pygame.K_SPACE in keys_pressed:
            if show_journal:
                show_journal = False
                continue
            if active_dialogue:
                dialogue_index += 1
                if dialogue_index >= len(dialogue_lines):
                    talked_to.add(active_dialogue)
                    active_dialogue = None
                    if len(talked_to) == 3:
                        show_journal = True
                continue
            else:
                for name, img, npc_rect, dialogue_hitbox in npc_data:
                    if character.rect.colliderect(dialogue_hitbox):
                        active_dialogue = name
                        dialogue_lines = npc_dialogues[name]
                        dialogue_index = 0
                        active_npc = npc_rect
                        break

        # Movement - check all pressed keys
        keys = pygame.key.get_pressed()
        dx = dy = 0
        direction = character.direction
        moving = False
        
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= PLAYER_SPEED
            direction = 1
            moving = True
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += PLAYER_SPEED
            direction = 2
            moving = True
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= PLAYER_SPEED
            direction = 3
            moving = True
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += PLAYER_SPEED
            direction = 0
            moving = True
            
        new_rect = character.rect.copy()
        new_rect.x += dx
        new_rect.y += dy
        
        if can_move_pixel(new_rect) and not collides_with_building(new_rect):
            character.rect = new_rect
            
        character.update(dt, moving, direction)
        
        # Check for NPC interaction
        interaction_indicator_visible = False
        current_npc = None
        if not active_dialogue:
            for name, img, npc_rect, dialogue_hitbox in npc_data:
                if character.rect.colliderect(dialogue_hitbox):
                    interaction_indicator_visible = True
                    current_npc = npc_rect
                    break

        # Draw everything
        draw_tilemap(screen, fork_map, tiles, offset_x, offset_y)
        
        for name, img, rect in buildings:
            screen.blit(img, rect.topleft)
        
        for name, img, npc_rect, dialogue_hitbox in npc_data:
            screen.blit(img, npc_rect.topleft)
            if DEBUG_INTERACTION:
                pygame.draw.rect(screen, (0, 255, 0), dialogue_hitbox, 2)
        
        character.draw(screen)
        
        # Draw touch controls if on iPad
        if TOUCH_CONTROLS:
            draw_touch_controls()
        
        if interaction_indicator_visible and current_npc and not active_dialogue:
            draw_interaction_indicator(current_npc)
        
        if active_dialogue:
            draw_dialogue_box(dialogue_lines[dialogue_index], active_npc)
        
        if show_journal:
            draw_journal_box("\n".join(journal_text))
        
        if DEBUG_INTERACTION:
            pygame.draw.rect(screen, (255, 0, 0), character.rect, 2)
        
        pygame.display.flip()
        await asyncio.sleep(0)  # Important for web

    pygame.quit()

# This must be at the very end
if __name__ == "__main__":
    asyncio.run(main())
