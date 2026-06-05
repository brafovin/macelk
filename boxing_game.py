import pygame
import sys
import math
import random
import time

pygame.init()

WIDTH, HEIGHT = 1280, 720
FPS = 60

BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
RED     = (200, 30, 30)
DARK_RED= (120, 10, 10)
BLUE    = (30, 80, 200)
DARK_BLUE=(10, 40, 120)
YELLOW  = (230, 200, 20)
GRAY    = (80, 80, 80)
DARK_GRAY=(40,40,40)
LIGHT_GRAY=(160,160,160)
ORANGE  = (220, 130, 20)
GREEN   = (30, 160, 50)
RING_CANVAS = (210, 180, 130)
ROPE_COLOR  = (180, 30, 30)
FLOOR_COLOR = (190, 160, 110)
CROWD_DARK  = (20, 10, 10)
SKIN        = (230, 190, 140)
GLOVE_RED   = (180, 20, 20)
GLOVE_BLUE  = (20, 40, 180)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("BOXING 64 — Ring Fighter")
clock = pygame.time.Clock()

font_big   = pygame.font.SysFont("impact", 72)
font_med   = pygame.font.SysFont("impact", 40)
font_small = pygame.font.SysFont("impact", 24)
font_tiny  = pygame.font.SysFont("impact", 18)

# ─── Ring geometry ────────────────────────────────────────────────────────────
RING_LEFT   = 160
RING_RIGHT  = 1120
RING_TOP    = 160
RING_BOTTOM = 580
RING_CX     = (RING_LEFT + RING_RIGHT) // 2
RING_CY     = (RING_TOP + RING_BOTTOM) // 2

# ─── Punch constants ──────────────────────────────────────────────────────────
PUNCH_JAB_DMG   = 8
PUNCH_CROSS_DMG = 18
PUNCH_BODY_DMG  = 12
PUNCH_UPPER_DMG = 20
PUNCH_RANGE     = 120
BLOCK_REDUCTION = 0.25

HOLD_THRESHOLD = 0.35   # seconds for cross

# ─── AI difficulty ────────────────────────────────────────────────────────────
AI_REACT_TIME  = 0.6
AI_BLOCK_CHANCE= 0.45
AI_ATTACK_INTERVAL = 1.2

# ══════════════════════════════════════════════════════════════════════════════
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 7)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed - 2
        self.life = random.randint(15, 30)
        self.max_life = self.life
        self.radius = random.randint(3, 7)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.3
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        r = int(self.color[0] * alpha)
        g = int(self.color[1] * alpha)
        b = int(self.color[2] * alpha)
        pygame.draw.circle(surf, (r, g, b), (int(self.x), int(self.y)), max(1, int(self.radius * alpha)))


# ══════════════════════════════════════════════════════════════════════════════
class HitFlash:
    def __init__(self, x, y, text, color=RED):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 45
        self.max_life = 45

    def update(self):
        self.y -= 1
        self.life -= 1

    def draw(self, surf):
        alpha = self.life / self.max_life
        size = int(20 + (1 - alpha) * 10)
        try:
            f = pygame.font.SysFont("impact", size)
        except Exception:
            f = font_small
        t = f.render(self.text, True, self.color)
        t.set_alpha(int(255 * alpha))
        surf.blit(t, (int(self.x) - t.get_width() // 2, int(self.y)))


# ══════════════════════════════════════════════════════════════════════════════
class Boxer:
    def __init__(self, x, y, name, color_scheme, is_player=False):
        self.x = float(x)
        self.y = float(y)
        self.name = name
        self.is_player = is_player
        self.color = color_scheme     # "red" or "blue"
        self.glove_color = GLOVE_RED if color_scheme == "red" else GLOVE_BLUE

        self.hp = 100
        self.max_hp = 100
        self.stamina = 100
        self.max_stamina = 100

        self.vx = 0.0
        self.vy = 0.0
        self.speed = 3.5
        self.facing = 1 if not is_player else -1   # +1 right, -1 left

        # stance / animation
        self.state      = "idle"   # idle, moving, punching, blocking, dodging, hurt, ko
        self.state_timer = 0
        self.bob_phase   = 0.0

        # punch
        self.punch_type   = None   # "jab_l","jab_r","cross_l","cross_r","body","upper"
        self.punch_side   = "left"
        self.punch_anim   = 0.0   # 0..1 progress
        self.punch_hit    = False

        # block
        self.blocking = False

        # dodge
        self.dodge_dir  = 0
        self.dodge_timer= 0

        # hurt flash
        self.hurt_flash = 0

        # ko
        self.ko_anim = 0.0

        # cooldown
        self.punch_cooldown = 0

        # damage flash
        self.flash_timer = 0

        # particles / labels stored externally, but we keep a list here
        self.particles: list[Particle] = []
        self.labels:    list[HitFlash] = []

    # ── drawing helpers ───────────────────────────────────────────────────────
    def _body_rect(self):
        return pygame.Rect(int(self.x) - 22, int(self.y) - 90, 44, 90)

    def draw(self, surf):
        bob = math.sin(self.bob_phase) * 3
        cx = int(self.x)
        cy = int(self.y) + int(bob)

        if self.state == "ko":
            self._draw_ko(surf, cx, cy)
        else:
            self._draw_stand(surf, cx, cy)

        # hurt flash overlay
        if self.flash_timer > 0:
            s = pygame.Surface((60, 120), pygame.SRCALPHA)
            alpha = int(180 * self.flash_timer / 10)
            s.fill((255, 60, 60, alpha))
            surf.blit(s, (cx - 30, cy - 120))
            self.flash_timer -= 1

        for p in self.particles[:]:
            p.update()
            p.draw(surf)
            if p.life <= 0:
                self.particles.remove(p)

        for lbl in self.labels[:]:
            lbl.update()
            lbl.draw(surf)
            if lbl.life <= 0:
                self.labels.remove(lbl)

    def _draw_stand(self, surf, cx, cy):
        gc = self.glove_color
        sk = SKIN

        punch_ext = 0
        if self.state == "punching" and self.punch_anim < 0.5:
            punch_ext = int(self.punch_anim / 0.5 * 50)
        elif self.state == "punching":
            punch_ext = int((1 - self.punch_anim) / 0.5 * 50)

        # legs
        pygame.draw.rect(surf, DARK_GRAY, (cx - 18, cy - 10, 14, 30), border_radius=4)
        pygame.draw.rect(surf, DARK_GRAY, (cx + 4, cy - 10, 14, 30), border_radius=4)
        # shorts
        shorts_color = RED if self.color == "red" else BLUE
        pygame.draw.rect(surf, shorts_color, (cx - 20, cy - 40, 40, 32), border_radius=6)
        # torso
        pygame.draw.rect(surf, sk, (cx - 18, cy - 85, 36, 48), border_radius=8)
        # head
        pygame.draw.circle(surf, sk, (cx, cy - 98), 20)
        # headgear
        hg_color = RED if self.color == "red" else BLUE
        pygame.draw.arc(surf, hg_color, (cx - 22, cy - 122, 44, 44), 0, math.pi, 6)
        pygame.draw.rect(surf, hg_color, (cx - 22, cy - 105, 44, 10), border_radius=3)
        # eyes
        eye_dx = 6 * self.facing
        pygame.draw.circle(surf, WHITE, (cx + eye_dx, cy - 100), 4)
        pygame.draw.circle(surf, BLACK, (cx + eye_dx + self.facing, cy - 100), 2)

        # arms / gloves
        if self.state == "blocking":
            # both arms raised
            pygame.draw.line(surf, sk, (cx - 14, cy - 70), (cx - 28, cy - 100), 8)
            pygame.draw.line(surf, sk, (cx + 14, cy - 70), (cx + 28, cy - 100), 8)
            pygame.draw.circle(surf, gc, (cx - 28, cy - 100), 14)
            pygame.draw.circle(surf, gc, (cx + 28, cy - 100), 14)
        else:
            is_left  = self.punch_side == "left"  if self.state == "punching" else False
            is_right = self.punch_side == "right" if self.state == "punching" else False
            is_body  = self.punch_type in ("body", "upper") if self.state == "punching" else False

            # left arm
            lx_end = cx - 28 - (punch_ext * self.facing if is_left and not is_body else 0)
            ly_end = cy - 82 + (20 if is_body and is_left else 0)
            pygame.draw.line(surf, sk, (cx - 14, cy - 68), (lx_end, ly_end), 8)
            pygame.draw.circle(surf, gc, (lx_end, ly_end), 14)

            # right arm
            rx_end = cx + 28 + (punch_ext * self.facing if is_right and not is_body else 0)
            ry_end = cy - 82 + (20 if is_body and is_right else 0)
            pygame.draw.line(surf, sk, (cx + 14, cy - 68), (rx_end, ry_end), 8)
            pygame.draw.circle(surf, gc, (rx_end, ry_end), 14)

    def _draw_ko(self, surf, cx, cy):
        pygame.draw.ellipse(surf, SKIN, (cx - 40, cy - 20, 80, 28))
        pygame.draw.ellipse(surf, DARK_GRAY, (cx - 30, cy - 5, 60, 24))
        pygame.draw.ellipse(surf, self.glove_color, (cx - 50, cy - 10, 28, 20))
        pygame.draw.ellipse(surf, self.glove_color, (cx + 22, cy - 10, 28, 20))
        pygame.draw.circle(surf, SKIN, (cx, cy - 22), 20)

    # ── logic ─────────────────────────────────────────────────────────────────
    def update(self, dt):
        self.bob_phase += 4 * dt
        if self.punch_cooldown > 0:
            self.punch_cooldown -= dt

        if self.state == "punching":
            self.punch_anim += dt * 4
            if self.punch_anim >= 1.0:
                self.state = "idle"
                self.punch_anim = 0.0
                self.punch_hit = False

        if self.state == "dodging":
            self.dodge_timer -= dt
            self.x += self.dodge_dir * 180 * dt
            if self.dodge_timer <= 0:
                self.state = "idle"

        if self.state == "hurt":
            self.state_timer -= dt
            if self.state_timer <= 0:
                self.state = "idle"

        if self.state == "ko":
            self.ko_anim = min(1.0, self.ko_anim + dt * 2)

        # movement
        if self.state in ("idle", "moving"):
            self.x += self.vx
            self.y += self.vy
            self.state = "moving" if (abs(self.vx) + abs(self.vy)) > 0.1 else "idle"

        # clamp to ring
        self.x = max(RING_LEFT + 30, min(RING_RIGHT - 30, self.x))
        self.y = max(RING_TOP  + 30, min(RING_BOTTOM - 20, self.y))

        # stamina regen
        if self.state != "punching":
            self.stamina = min(self.max_stamina, self.stamina + 12 * dt)

    def start_punch(self, ptype, side):
        if self.state in ("ko", "hurt", "blocking"):
            return False
        if self.punch_cooldown > 0:
            return False
        cost = 10 if ptype in ("jab_l","jab_r") else 20
        if self.stamina < cost:
            return False
        self.stamina -= cost
        self.state      = "punching"
        self.punch_type = ptype
        self.punch_side = side
        self.punch_anim = 0.0
        self.punch_hit  = False
        cd = 0.3 if ptype in ("jab_l","jab_r") else 0.5
        self.punch_cooldown = cd
        return True

    def start_block(self):
        if self.state not in ("ko", "punching"):
            self.state    = "blocking"
            self.blocking = True

    def stop_block(self):
        self.blocking = False
        if self.state == "blocking":
            self.state = "idle"

    def dodge(self, direction):
        if self.state in ("ko", "punching"):
            return
        self.state      = "dodging"
        self.dodge_dir  = direction
        self.dodge_timer= 0.25

    def take_hit(self, damage, hit_type="jab"):
        if self.state == "ko":
            return 0
        multiplier = BLOCK_REDUCTION if self.blocking else 1.0
        dmg = int(damage * multiplier)
        self.hp = max(0, self.hp - dmg)
        self.flash_timer = 10
        if not self.blocking:
            self.state       = "hurt"
            self.state_timer = 0.18
        # spawn particles
        for _ in range(random.randint(4, 10)):
            self.particles.append(Particle(self.x, self.y - 80, (255, 80, 80)))

        # label
        label_map = {"jab": f"-{dmg}", "cross": f"CROSS -{dmg}", "body": f"BODY -{dmg}", "upper": f"UPPER! -{dmg}"}
        lbl_text  = label_map.get(hit_type, f"-{dmg}")
        lbl_color = ORANGE if self.blocking else RED
        self.labels.append(HitFlash(self.x + random.randint(-20, 20), self.y - 110, lbl_text, lbl_color))

        if self.hp <= 0:
            self.state = "ko"
        return dmg

    def punch_contact_point(self):
        ext = 60
        if self.punch_side == "left":
            return (self.x - ext * self.facing, self.y - 82)
        else:
            return (self.x + ext * self.facing, self.y - 82)


# ══════════════════════════════════════════════════════════════════════════════
class AIController:
    def __init__(self, boxer: Boxer, target: Boxer):
        self.boxer  = boxer
        self.target = target
        self.action_timer = random.uniform(0.5, AI_ATTACK_INTERVAL)
        self.phase = "approach"   # approach / attack / retreat / block

    def update(self, dt):
        b = self.boxer
        t = self.target
        if b.state == "ko":
            return

        dx = t.x - b.x
        dy = t.y - b.y
        dist = math.hypot(dx, dy)

        b.facing = 1 if dx > 0 else -1

        self.action_timer -= dt

        if self.action_timer <= 0:
            self.action_timer = random.uniform(0.4, AI_ATTACK_INTERVAL)

            if dist < PUNCH_RANGE + 20:
                roll = random.random()
                if roll < 0.15:
                    b.start_block()
                    pygame.time.set_timer(pygame.USEREVENT + 10, 400)
                elif roll < 0.30:
                    b.dodge(random.choice([-1, 1]))
                else:
                    choices = [
                        ("jab_l", "left"),
                        ("jab_r", "right"),
                        ("cross_l", "left"),
                        ("cross_r", "right"),
                        ("body", "left"),
                        ("upper", "right"),
                    ]
                    pt, side = random.choice(choices)
                    b.start_punch(pt, side)
            else:
                self.phase = "approach"

        # movement
        b.vx = 0; b.vy = 0
        if b.state in ("idle", "moving"):
            if self.phase == "approach" and dist > PUNCH_RANGE - 10:
                speed = b.speed * 0.7
                b.vx = (dx / dist) * speed if dist > 0 else 0
                b.vy = (dy / dist) * speed if dist > 0 else 0
            elif dist < 40:
                b.vx = -(dx / dist) * b.speed * 0.5
                b.vy = -(dy / dist) * b.speed * 0.5

        if b.blocking and random.random() < 0.02:
            b.stop_block()


# ══════════════════════════════════════════════════════════════════════════════
def draw_ring(surf):
    # crowd / background
    surf.fill((15, 8, 8))

    # crowd blobs
    for i in range(0, WIDTH, 30):
        h = random.randint(20, 60)
        c = (random.randint(20, 60), random.randint(10, 30), random.randint(10, 30))
        pygame.draw.ellipse(surf, c, (i, HEIGHT - h - 20, 26, h))

    surf.fill((15, 8, 8))  # re-fill solid bg

    # floor shadow
    pygame.draw.ellipse(surf, (40, 30, 20), (RING_LEFT + 20, RING_BOTTOM - 20, RING_RIGHT - RING_LEFT - 40, 60))

    # canvas
    pygame.draw.rect(surf, FLOOR_COLOR, (RING_LEFT, RING_TOP, RING_RIGHT - RING_LEFT, RING_BOTTOM - RING_TOP), border_radius=4)
    # canvas lines
    for lx in range(RING_LEFT + 80, RING_RIGHT, 80):
        pygame.draw.line(surf, (180, 150, 100), (lx, RING_TOP), (lx, RING_BOTTOM), 1)
    for ly in range(RING_TOP + 60, RING_BOTTOM, 60):
        pygame.draw.line(surf, (180, 150, 100), (RING_LEFT, ly), (RING_RIGHT, ly), 1)

    # centre circle
    pygame.draw.circle(surf, (170, 140, 90), (RING_CX, RING_CY), 80, 2)

    # posts
    post_positions = [(RING_LEFT, RING_TOP), (RING_RIGHT, RING_TOP), (RING_LEFT, RING_BOTTOM), (RING_RIGHT, RING_BOTTOM)]
    for px, py in post_positions:
        pygame.draw.rect(surf, GRAY, (px - 8, py - 8, 16, 16))
        pygame.draw.rect(surf, LIGHT_GRAY, (px - 6, py - 50, 12, 50))

    # ropes (3 levels)
    for offset in [15, 30, 45]:
        pygame.draw.line(surf, ROPE_COLOR, (RING_LEFT, RING_TOP - offset), (RING_RIGHT, RING_TOP - offset), 3)
        pygame.draw.line(surf, ROPE_COLOR, (RING_LEFT, RING_BOTTOM + offset), (RING_RIGHT, RING_BOTTOM + offset), 3)
        pygame.draw.line(surf, ROPE_COLOR, (RING_LEFT - offset, RING_TOP), (RING_LEFT - offset, RING_BOTTOM), 3)
        pygame.draw.line(surf, ROPE_COLOR, (RING_RIGHT + offset, RING_TOP), (RING_RIGHT + offset, RING_BOTTOM), 3)

    # spotlights
    for sx in [RING_CX - 200, RING_CX, RING_CX + 200]:
        ssurf = pygame.Surface((300, 300), pygame.SRCALPHA)
        pygame.draw.circle(ssurf, (255, 255, 200, 18), (150, 150), 150)
        surf.blit(ssurf, (sx - 150, RING_TOP - 150))


def draw_hud(surf, player: Boxer, enemy: Boxer, round_num, round_timer):
    # player HP bar
    pygame.draw.rect(surf, DARK_RED,  (30, 30, 300, 28), border_radius=6)
    w = int(300 * player.hp / player.max_hp)
    pygame.draw.rect(surf, RED,       (30, 30, w, 28), border_radius=6)
    pygame.draw.rect(surf, WHITE,     (30, 30, 300, 28), 2, border_radius=6)
    t = font_small.render(f"{player.name}  {player.hp}HP", True, WHITE)
    surf.blit(t, (35, 34))

    # player stamina bar
    pygame.draw.rect(surf, (20, 60, 20), (30, 64, 300, 14), border_radius=4)
    sw = int(300 * player.stamina / player.max_stamina)
    pygame.draw.rect(surf, GREEN,     (30, 64, sw, 14), border_radius=4)

    # enemy HP bar (right side)
    pygame.draw.rect(surf, DARK_BLUE, (WIDTH - 330, 30, 300, 28), border_radius=6)
    w2 = int(300 * enemy.hp / enemy.max_hp)
    pygame.draw.rect(surf, BLUE, (WIDTH - 330 + (300 - w2), 30, w2, 28), border_radius=6)
    pygame.draw.rect(surf, WHITE, (WIDTH - 330, 30, 300, 28), 2, border_radius=6)
    t2 = font_small.render(f"{enemy.hp}HP  {enemy.name}", True, WHITE)
    surf.blit(t2, (WIDTH - 330 + 300 - t2.get_width() - 5, 34))

    # enemy stamina
    pygame.draw.rect(surf, (20, 60, 20), (WIDTH - 330, 64, 300, 14), border_radius=4)
    sw2 = int(300 * enemy.stamina / enemy.max_stamina)
    pygame.draw.rect(surf, GREEN, (WIDTH - 330 + (300 - sw2), 64, sw2, 14), border_radius=4)

    # round info
    rt = font_med.render(f"RUNDA {round_num}", True, YELLOW)
    surf.blit(rt, (WIDTH // 2 - rt.get_width() // 2, 20))
    secs = max(0, int(round_timer))
    ts = font_small.render(f"{secs // 60:02d}:{secs % 60:02d}", True, WHITE)
    surf.blit(ts, (WIDTH // 2 - ts.get_width() // 2, 58))

    # controls hint
    hints = [
        "WASD=ruch  Q/E=unik  SPACJA=garda",
        "LPM=jab L  PPM=jab P  (dłużej=cross)",
        "C=podbródkowy  R=jab w brzuch",
    ]
    for i, h in enumerate(hints):
        ht = font_tiny.render(h, True, (140, 140, 140))
        surf.blit(ht, (WIDTH // 2 - ht.get_width() // 2, HEIGHT - 60 + i * 18))


def check_punch_hit(attacker: Boxer, defender: Boxer):
    if attacker.state != "punching":
        return
    if attacker.punch_hit:
        return
    if attacker.punch_anim < 0.3 or attacker.punch_anim > 0.7:
        return

    cx, cy = attacker.punch_contact_point()
    dx = defender.x - cx
    dy = (defender.y - 85) - cy
    dist = math.hypot(dx, dy)
    if dist < 50:
        attacker.punch_hit = True
        ptype = attacker.punch_type
        if ptype in ("jab_l", "jab_r"):
            dmg  = PUNCH_JAB_DMG
            htype = "jab"
        elif ptype in ("cross_l", "cross_r"):
            dmg  = PUNCH_CROSS_DMG
            htype = "cross"
        elif ptype == "body":
            dmg  = PUNCH_BODY_DMG
            htype = "body"
        else:
            dmg  = PUNCH_UPPER_DMG
            htype = "upper"
        defender.take_hit(dmg, htype)


# ══════════════════════════════════════════════════════════════════════════════
# MENU
# ══════════════════════════════════════════════════════════════════════════════
def draw_menu_bg(surf, t):
    surf.fill((8, 4, 4))
    for i in range(0, WIDTH, 40):
        alpha = int(abs(math.sin(t * 0.8 + i * 0.03)) * 60 + 10)
        c = (alpha, alpha // 3, alpha // 3)
        pygame.draw.line(surf, c, (i, 0), (i, HEIGHT))

    # title glow
    glow = pygame.Surface((700, 140), pygame.SRCALPHA)
    glow.fill((180, 0, 0, 30))
    surf.blit(glow, (WIDTH // 2 - 350, 80))

    title = font_big.render("BOXING  64", True, YELLOW)
    shadow = font_big.render("BOXING  64", True, (80, 50, 0))
    surf.blit(shadow, (WIDTH // 2 - title.get_width() // 2 + 4, 104))
    surf.blit(title,  (WIDTH // 2 - title.get_width() // 2, 100))

    sub = font_med.render("RING FIGHTER", True, RED)
    surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 180))


def menu_screen():
    options = ["NOWA GRA", "STEROWANIE", "WYJŚCIE"]
    selected = 0
    t = 0.0

    while True:
        dt = clock.tick(FPS) / 1000.0
        t += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                if event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if selected == 0:
                        return "game"
                    elif selected == 1:
                        controls_screen()
                    else:
                        pygame.quit(); sys.exit()

        draw_menu_bg(screen, t)

        for i, opt in enumerate(options):
            color = YELLOW if i == selected else LIGHT_GRAY
            scale = 1.1 if i == selected else 1.0
            size = int(44 * scale)
            try:
                f = pygame.font.SysFont("impact", size)
            except Exception:
                f = font_med
            txt = f.render(("► " if i == selected else "  ") + opt, True, color)
            y = 300 + i * 80
            screen.blit(txt, (WIDTH // 2 - txt.get_width() // 2, y))

        ver = font_tiny.render("v1.0  |  64-bit Ring Fighter", True, GRAY)
        screen.blit(ver, (WIDTH // 2 - ver.get_width() // 2, HEIGHT - 30))

        pygame.display.flip()


def controls_screen():
    lines = [
        ("W", "Krok do przodu"),
        ("S", "Krok do tyłu"),
        ("A", "Krok w lewo"),
        ("D", "Krok w prawo"),
        ("Q", "Unik w lewo"),
        ("E", "Unik w prawo"),
        ("LPM", "Lewy jab"),
        ("PPM", "Prawy jab"),
        ("LPM (dłużej)", "Lewy cross"),
        ("PPM (dłużej)", "Prawy cross"),
        ("SPACJA", "Garda"),
        ("C", "Podbródkowy"),
        ("R", "Jab w brzuch"),
        ("ESC", "Menu"),
    ]
    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_RETURN):
                return

        screen.fill((10, 5, 5))
        t = font_big.render("STEROWANIE", True, YELLOW)
        screen.blit(t, (WIDTH // 2 - t.get_width() // 2, 30))

        for i, (key, desc) in enumerate(lines):
            col = 2
            row = i % ((len(lines) + 1) // col)
            col_x = WIDTH // 4 + (i // ((len(lines) + 1) // col)) * WIDTH // 2 - 120
            y = 130 + row * 38
            kt = font_small.render(key, True, YELLOW)
            dt_ = font_small.render(desc, True, WHITE)
            screen.blit(kt, (col_x, y))
            screen.blit(dt_, (col_x + 160, y))

        back = font_small.render("[ ESC / ENTER = wróć ]", True, GRAY)
        screen.blit(back, (WIDTH // 2 - back.get_width() // 2, HEIGHT - 40))
        pygame.display.flip()


def result_screen(winner: str, player_hp, enemy_hp):
    t = 0.0
    while True:
        dt = clock.tick(FPS) / 1000.0
        t += dt
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return "menu"
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()

        draw_menu_bg(screen, t)
        result_color = GREEN if winner == "PLAYER" else RED
        result_text  = "WYGRAŁEŚ!" if winner == "PLAYER" else "PRZEGRAŁEŚ!"
        rt = font_big.render(result_text, True, result_color)
        screen.blit(rt, (WIDTH // 2 - rt.get_width() // 2, 180))

        ko_t = font_med.render("NOKAUT!" if min(player_hp, enemy_hp) == 0 else "KONIEC RUNDY", True, YELLOW)
        screen.blit(ko_t, (WIDTH // 2 - ko_t.get_width() // 2, 280))

        hint = font_small.render("ENTER = Menu główne   ESC = Wyjście", True, WHITE)
        screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 400))
        pygame.display.flip()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN GAME LOOP
# ══════════════════════════════════════════════════════════════════════════════
def game_loop():
    player = Boxer(RING_CX - 150, RING_CY + 60, "GRACZ", "red",  is_player=True)
    enemy  = Boxer(RING_CX + 150, RING_CY + 60, "RYWAL", "blue", is_player=False)
    player.facing = 1
    enemy.facing  = -1

    ai = AIController(enemy, player)

    # mouse hold timers
    lmb_held = 0.0
    rmb_held = 0.0
    lmb_down = False
    rmb_down = False

    round_num   = 1
    round_timer = 120.0   # 2 minutes per round
    max_rounds  = 3

    screen_flash = 0

    while True:
        dt = clock.tick(FPS) / 1000.0
        round_timer -= dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "menu"
                if event.key == pygame.K_SPACE:
                    player.start_block()
                if event.key == pygame.K_c:
                    player.start_punch("upper", "right")
                if event.key == pygame.K_r:
                    player.start_punch("body", "left")
                if event.key == pygame.K_q:
                    player.dodge(-1)
                if event.key == pygame.K_e:
                    player.dodge(1)

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    player.stop_block()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    lmb_down = True
                    lmb_held = 0.0
                if event.button == 3:
                    rmb_down = True
                    rmb_held = 0.0

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if lmb_down:
                        if lmb_held < HOLD_THRESHOLD:
                            player.start_punch("jab_l", "left")
                        else:
                            player.start_punch("cross_l", "left")
                    lmb_down = False
                    lmb_held = 0.0
                if event.button == 3:
                    if rmb_down:
                        if rmb_held < HOLD_THRESHOLD:
                            player.start_punch("jab_r", "right")
                        else:
                            player.start_punch("cross_r", "right")
                    rmb_down = False
                    rmb_held = 0.0

        # hold timers
        if lmb_down:
            lmb_held += dt
        if rmb_down:
            rmb_held += dt

        # WASD movement
        keys = pygame.key.get_pressed()
        player.vx = 0; player.vy = 0
        if player.state in ("idle", "moving"):
            if keys[pygame.K_a]: player.vx = -player.speed
            if keys[pygame.K_d]: player.vx =  player.speed
            if keys[pygame.K_w]: player.vy = -player.speed
            if keys[pygame.K_s]: player.vy =  player.speed

        # update facing
        dx = enemy.x - player.x
        player.facing = 1 if dx > 0 else -1

        # update
        player.update(dt)
        enemy.update(dt)
        ai.update(dt)

        # hit detection
        check_punch_hit(player, enemy)
        check_punch_hit(enemy, player)

        # screen flash on big hit
        if screen_flash > 0:
            screen_flash -= 1

        # KO check
        if player.hp <= 0 or enemy.hp <= 0:
            winner = "PLAYER" if enemy.hp <= 0 else "ENEMY"
            # draw one last frame with KO
            draw_ring(screen)
            player.draw(screen)
            enemy.draw(screen)
            draw_hud(screen, player, enemy, round_num, round_timer)
            ko_txt = font_big.render("K.O.!", True, YELLOW)
            screen.blit(ko_txt, (WIDTH // 2 - ko_txt.get_width() // 2, HEIGHT // 2 - 60))
            pygame.display.flip()
            pygame.time.wait(2000)
            return result_screen(winner, player.hp, enemy.hp)

        if round_timer <= 0:
            winner = "PLAYER" if player.hp > enemy.hp else "ENEMY"
            return result_screen(winner, player.hp, enemy.hp)

        # ── draw ─────────────────────────────────────────────────────────────
        draw_ring(screen)

        if screen_flash > 0:
            flash_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash_surf.fill((255, 255, 255, screen_flash * 8))
            screen.blit(flash_surf, (0, 0))

        player.draw(screen)
        enemy.draw(screen)
        draw_hud(screen, player, enemy, round_num, round_timer)

        pygame.display.flip()

    return "menu"


# ══════════════════════════════════════════════════════════════════════════════
def main():
    while True:
        action = menu_screen()
        if action == "game":
            result = game_loop()
            if result == "menu":
                continue


if __name__ == "__main__":
    main()
