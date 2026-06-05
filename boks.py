#!/usr/bin/env python3
"""Gra bokserska 2D - walka na ringu."""

import pygame
import sys
import math
import random
import time

pygame.init()

WIDTH, HEIGHT = 1280, 720
FPS = 60

WHITE   = (255, 255, 255)
BLACK   = (0,   0,   0)
RED     = (200,  30,  30)
DARK_RED= (140,  10,  10)
BLUE    = (30,   80, 200)
DARK_BLUE=(10,   40, 140)
YELLOW  = (255, 220,   0)
GRAY    = (160, 160, 160)
DARK_GRAY=(80,  80,  80)
LIGHT   = (240, 220, 190)
CANVAS  = (220, 200, 160)
ROPE    = (180, 120,  40)
SKIN    = (220, 180, 140)
SKIN2   = (180, 130,  90)
BG_COLOR= (30,  20,  10)
GREEN   = (40, 180,  40)
ORANGE  = (255, 140,   0)

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("RING BOKS 64-bit")
clock = pygame.time.Clock()

try:
    font_big   = pygame.font.SysFont("Arial", 72, bold=True)
    font_med   = pygame.font.SysFont("Arial", 36, bold=True)
    font_small = pygame.font.SysFont("Arial", 24)
    font_tiny  = pygame.font.SysFont("Arial", 18)
except Exception:
    font_big   = pygame.font.Font(None, 72)
    font_med   = pygame.font.Font(None, 36)
    font_small = pygame.font.Font(None, 24)
    font_tiny  = pygame.font.Font(None, 18)


# ─── Ring ────────────────────────────────────────────────────────────────────

RING_LEFT   = 160
RING_RIGHT  = WIDTH - 160
RING_TOP    = 160
RING_BOTTOM = HEIGHT - 120
RING_CX     = (RING_LEFT + RING_RIGHT) // 2
RING_CY     = (RING_TOP  + RING_BOTTOM) // 2


def draw_ring(surf):
    # Floor
    pygame.draw.rect(surf, CANVAS,
                     (RING_LEFT, RING_TOP, RING_RIGHT - RING_LEFT, RING_BOTTOM - RING_TOP))
    # Center line
    pygame.draw.line(surf, (200, 180, 140),
                     (RING_CX, RING_TOP), (RING_CX, RING_BOTTOM), 2)
    # Corner posts
    post_r = 14
    corners = [(RING_LEFT, RING_TOP), (RING_RIGHT, RING_TOP),
               (RING_LEFT, RING_BOTTOM), (RING_RIGHT, RING_BOTTOM)]
    post_colors = [RED, BLUE, RED, BLUE]
    for (cx, cy), col in zip(corners, post_colors):
        pygame.draw.circle(surf, col, (cx, cy), post_r)
        pygame.draw.circle(surf, WHITE, (cx, cy), post_r, 3)

    # Ropes (3 levels)
    for oy in [0, 30, 60]:
        y = RING_TOP - 20 + oy
        pygame.draw.line(surf, ROPE, (RING_LEFT, y), (RING_RIGHT, y), 6)
    for oy in [0, 30, 60]:
        y = RING_BOTTOM + 20 - oy
        pygame.draw.line(surf, ROPE, (RING_LEFT, y), (RING_RIGHT, y), 6)
    for ox in [0, 30, 60]:
        x = RING_LEFT - 20 + ox
        pygame.draw.line(surf, ROPE, (x, RING_TOP), (x, RING_BOTTOM), 6)
    for ox in [0, 30, 60]:
        x = RING_RIGHT + 20 - ox
        pygame.draw.line(surf, ROPE, (x, RING_TOP), (x, RING_BOTTOM), 6)

    # Border
    pygame.draw.rect(surf, DARK_GRAY,
                     (RING_LEFT, RING_TOP, RING_RIGHT - RING_LEFT, RING_BOTTOM - RING_TOP), 4)


# ─── Particles / Hit effects ─────────────────────────────────────────────────

particles = []


def spawn_hit(x, y, color=RED, count=12):
    for _ in range(count):
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 7)
        particles.append({
            "x": x, "y": y,
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed - 2,
            "life": random.randint(15, 30),
            "color": color,
            "r": random.randint(3, 7),
        })


def update_particles(surf):
    dead = []
    for p in particles:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["vy"] += 0.3
        p["life"] -= 1
        alpha = max(0, p["life"] * 8)
        r = max(1, p["r"] - (30 - p["life"]) // 8)
        col = p["color"]
        pygame.draw.circle(surf, col, (int(p["x"]), int(p["y"])), r)
        if p["life"] <= 0:
            dead.append(p)
    for d in dead:
        particles.remove(d)


# ─── Floating damage numbers ──────────────────────────────────────────────────

floats = []


def spawn_float(x, y, text, color=YELLOW):
    floats.append({"x": x, "y": y, "text": text, "color": color, "life": 50})


def update_floats(surf):
    dead = []
    for f in floats:
        f["y"] -= 1
        f["life"] -= 1
        alpha = max(0, f["life"] * 5)
        surf_txt = font_small.render(f["text"], True, f["color"])
        surf.blit(surf_txt, (int(f["x"]) - surf_txt.get_width() // 2, int(f["y"])))
        if f["life"] <= 0:
            dead.append(f)
    for d in dead:
        floats.remove(d)


# ─── Boxer ───────────────────────────────────────────────────────────────────

class Boxer:
    WALK_SPEED  = 3.5
    DODGE_DIST  = 55
    DODGE_TIME  = 14

    PUNCH_RANGE = 95
    JAB_DMG     = 8
    CROSS_DMG   = 18
    UPPER_DMG   = 22
    BODY_DMG    = 12

    MAX_HP      = 100
    MAX_STAM    = 100
    STAM_REGEN  = 0.25
    GUARD_DRAIN = 0.4

    def __init__(self, x, y, color, color2, name, facing=1):
        self.x, self.y   = float(x), float(y)
        self.color       = color
        self.color2      = color2
        self.name        = name
        self.facing      = facing   # 1 = right, -1 = left

        self.hp          = self.MAX_HP
        self.stam        = self.MAX_STAM

        self.guarding    = False
        self.dodge_dir   = 0
        self.dodge_timer = 0

        self.punch_state  = None   # None / 'jab_l' / 'jab_r' / 'cross_l' / 'cross_r' / 'upper' / 'body'
        self.punch_timer  = 0
        self.punch_hit    = False
        self.stun_timer   = 0

        self.knockdown    = False
        self.knockdown_t  = 0

        self.flash_timer  = 0

        # For floaty KO animation
        self.vy          = 0.0

    # -- drawing helpers -------------------------------------------------------

    def draw(self, surf):
        if self.knockdown:
            self._draw_knockdown(surf)
            return
        if self.flash_timer > 0 and self.flash_timer % 4 < 2:
            self.flash_timer -= 1
            return
        if self.flash_timer > 0:
            self.flash_timer -= 1

        x, y = int(self.x), int(self.y)
        f = self.facing

        # Shadow
        pygame.draw.ellipse(surf, (120, 100, 80),
                            (x - 28, y + 56, 56, 14))

        # Legs
        pygame.draw.rect(surf, self.color2,
                         (x - 16*f, y + 30, 14, 30))
        pygame.draw.rect(surf, self.color2,
                         (x + 2*f,  y + 30, 14, 30))

        # Body / torso
        if self.guarding:
            # Crouched guard
            pygame.draw.rect(surf, self.color,  (x - 18, y + 4, 36, 32), border_radius=8)
        else:
            pygame.draw.rect(surf, self.color,  (x - 18, y,     36, 40), border_radius=8)

        # Head
        head_y = y - 22 if not self.guarding else y - 14
        pygame.draw.circle(surf, SKIN, (x, head_y), 18)
        # Eye
        eye_x = x + 7 * f
        pygame.draw.circle(surf, BLACK, (eye_x, head_y - 4), 3)
        # Mouth guard
        pygame.draw.rect(surf, RED, (x - 8, head_y + 6, 16, 5), border_radius=2)

        # Arms / gloves
        self._draw_arms(surf, x, y, f)

    def _draw_arms(self, surf, x, y, f):
        pt = self.punch_timer
        ps = self.punch_state

        glove_r = RED if self.color == RED else BLUE
        glove_c = DARK_RED if self.color == RED else DARK_BLUE

        # Default arm positions
        lx, ly = x - 18*f, y + 8
        rx, ry = x + 18*f, y + 8

        if ps in ('jab_l', 'cross_l') and pt > 0:
            ext = min(pt * 3, 55)
            lx = x + (ext - 18) * f
            ly = y + 5
        if ps in ('jab_r', 'cross_r') and pt > 0:
            ext = min(pt * 3, 55)
            rx = x + (ext + 18) * f
            ry = y + 5
        if ps == 'upper' and pt > 0:
            ext = min(pt * 2, 30)
            lx = x - 10 * f
            ly = y + 5 - ext
        if ps == 'body' and pt > 0:
            ext = min(pt * 2, 25)
            rx = x + (18 + ext) * f
            ry = y + 22

        # Draw arms as lines + gloves
        pygame.draw.line(surf, self.color, (x - 10*f, y + 10), (lx, ly), 7)
        pygame.draw.circle(surf, glove_r, (lx, ly), 11)
        pygame.draw.circle(surf, glove_c, (lx, ly), 11, 2)

        pygame.draw.line(surf, self.color, (x + 10*f, y + 10), (rx, ry), 7)
        pygame.draw.circle(surf, glove_r, (rx, ry), 11)
        pygame.draw.circle(surf, glove_c, (rx, ry), 11, 2)

    def _draw_knockdown(self, surf):
        x, y = int(self.x), int(self.y)
        # Lying on ground
        pygame.draw.ellipse(surf, (120, 100, 80), (x - 42, y + 58, 84, 18))
        pygame.draw.rect(surf, self.color,  (x - 40, y + 28, 80, 30), border_radius=10)
        pygame.draw.circle(surf, SKIN, (x - 26, y + 22), 18)

    # -- HUD bars --------------------------------------------------------------

    def draw_hud(self, surf, left_side):
        bar_w = 320
        bar_h = 22
        bx = 40 if left_side else WIDTH - 40 - bar_w

        # Name
        col = RED if self.color == RED else BLUE
        lbl = font_small.render(self.name, True, col)
        surf.blit(lbl, (bx, 14))

        # HP bar
        pygame.draw.rect(surf, DARK_GRAY, (bx, 44, bar_w, bar_h), border_radius=6)
        hp_frac = max(0, self.hp / self.MAX_HP)
        hp_col = GREEN if hp_frac > 0.5 else ORANGE if hp_frac > 0.25 else RED
        pygame.draw.rect(surf, hp_col,   (bx, 44, int(bar_w * hp_frac), bar_h), border_radius=6)
        pygame.draw.rect(surf, WHITE,    (bx, 44, bar_w, bar_h), 2, border_radius=6)
        ht = font_tiny.render(f"HP {int(self.hp)}", True, WHITE)
        surf.blit(ht, (bx + 6, 47))

        # Stamina bar
        pygame.draw.rect(surf, DARK_GRAY, (bx, 72, bar_w, 14), border_radius=5)
        st_frac = max(0, self.stam / self.MAX_STAM)
        pygame.draw.rect(surf, YELLOW,   (bx, 72, int(bar_w * st_frac), 14), border_radius=5)
        pygame.draw.rect(surf, WHITE,    (bx, 72, bar_w, 14), 2, border_radius=5)
        st_txt = font_tiny.render(f"STAM {int(self.stam)}", True, BLACK)
        surf.blit(st_txt, (bx + 6, 73))

        if self.knockdown:
            kd = font_med.render("NOKAUT!", True, RED)
            surf.blit(kd, (bx, 94))

    # -- movement & actions ----------------------------------------------------

    def move(self, dx, dy):
        if self.stun_timer > 0 or self.knockdown:
            return
        if self.punch_timer > 6:
            return
        nx = self.x + dx * self.WALK_SPEED
        ny = self.y + dy * self.WALK_SPEED
        nx = max(RING_LEFT + 30, min(RING_RIGHT - 30, nx))
        ny = max(RING_TOP + 30,  min(RING_BOTTOM - 30, ny))
        self.x, self.y = nx, ny

    def dodge(self, direction):
        if self.stun_timer > 0 or self.knockdown:
            return
        if self.stam < 15:
            return
        self.dodge_dir   = direction
        self.dodge_timer = self.DODGE_TIME
        self.stam       -= 15

    def start_punch(self, kind):
        if self.stun_timer > 0 or self.knockdown:
            return
        costs = {'jab_l': 5, 'jab_r': 5, 'cross_l': 14, 'cross_r': 14,
                 'upper': 18, 'body': 10}
        if self.stam < costs.get(kind, 5):
            return
        if self.punch_timer > 0:
            return
        self.punch_state = kind
        self.punch_timer = 18
        self.punch_hit   = False
        self.stam -= costs[kind]

    def update(self):
        if self.knockdown:
            self.knockdown_t -= 1
            if self.knockdown_t <= 0:
                self.knockdown = False
                self.hp = max(1, self.hp)
            return

        # Dodge movement
        if self.dodge_timer > 0:
            self.x += self.dodge_dir * 5
            self.x  = max(RING_LEFT + 30, min(RING_RIGHT - 30, self.x))
            self.dodge_timer -= 1

        # Punch countdown
        if self.punch_timer > 0:
            self.punch_timer -= 1
            if self.punch_timer == 0:
                self.punch_state = None

        # Stun
        if self.stun_timer > 0:
            self.stun_timer -= 1

        # Guard stamina drain
        if self.guarding:
            self.stam = max(0, self.stam - self.GUARD_DRAIN)
        else:
            self.stam = min(self.MAX_STAM, self.stam + self.STAM_REGEN)

    def get_fist_pos(self):
        """Return current active fist world position."""
        if self.punch_state is None:
            return None
        f = self.facing
        x, y = self.x, self.y
        pt   = self.punch_timer

        if self.punch_state in ('jab_l', 'cross_l'):
            ext = min((18 - pt) * 3, 55)
            return (x + (ext - 18) * f, y + 5)
        if self.punch_state in ('jab_r', 'cross_r'):
            ext = min((18 - pt) * 3, 55)
            return (x + (ext + 18) * f, y + 5)
        if self.punch_state == 'upper':
            ext = min((18 - pt) * 2, 30)
            return (x - 10 * f, y + 5 - ext)
        if self.punch_state == 'body':
            ext = min((18 - pt) * 2, 25)
            return (x + (18 + ext) * f, y + 22)
        return None

    def try_hit(self, target):
        """Check if this boxer's fist hits the target."""
        if self.punch_hit:
            return
        fist = self.get_fist_pos()
        if fist is None:
            return
        # Only hit in the forward extension window
        if self.punch_timer > 10:
            return
        fx, fy = fist
        dist = math.hypot(fx - target.x, fy - target.y)
        if dist > self.PUNCH_RANGE:
            return

        dmg_map = {
            'jab_l':   self.JAB_DMG,
            'jab_r':   self.JAB_DMG,
            'cross_l': self.CROSS_DMG,
            'cross_r': self.CROSS_DMG,
            'upper':   self.UPPER_DMG,
            'body':    self.BODY_DMG,
        }
        dmg = dmg_map.get(self.punch_state, 8)

        if target.guarding:
            dmg = max(1, dmg // 3)
            spawn_hit(int(target.x), int(target.y - 20), GRAY, 6)
            spawn_float(target.x, target.y - 40, f"-{dmg} (blok)", GRAY)
        else:
            if target.dodge_timer > 4:
                spawn_float(target.x, target.y - 40, "UNIK!", GREEN)
                self.punch_hit = True
                return
            spawn_hit(int(target.x), int(target.y - 20), RED, 14)
            label = {
                'jab_l': 'JAB!', 'jab_r': 'JAB!',
                'cross_l': 'CROSS!', 'cross_r': 'CROSS!',
                'upper': 'UPPER!', 'body': 'BODY!',
            }.get(self.punch_state, 'HIT!')
            spawn_float(target.x, target.y - 50, f"{label} -{dmg}", YELLOW)
            if self.punch_state in ('cross_l', 'cross_r', 'upper'):
                target.stun_timer = 25
            target.flash_timer = 20

        target.hp -= dmg
        self.punch_hit = True

        if target.hp <= 0:
            target.hp = 0
            target.knockdown   = True
            target.knockdown_t = 180
            spawn_float(target.x, target.y - 70, "NOKAUT!!!", RED)


# ─── AI opponent ─────────────────────────────────────────────────────────────

class AIBoxer(Boxer):
    def __init__(self, x, y, difficulty=1):
        super().__init__(x, y, BLUE, DARK_BLUE, "PRZECIWNIK", facing=-1)
        self.difficulty  = difficulty  # 1=easy 2=medium 3=hard
        self.ai_timer    = 0
        self.ai_state    = 'approach'
        self.idle_timer  = 0

    def ai_update(self, player):
        if self.knockdown or player.knockdown:
            return

        self.ai_timer -= 1
        if self.ai_timer > 0:
            return

        dist  = math.hypot(self.x - player.x, self.y - player.y)
        react = max(5, 30 - self.difficulty * 8)  # faster reaction at high diff

        # Dodge incoming punches
        if player.punch_timer in range(8, 14) and not player.punch_hit:
            if random.random() < 0.25 * self.difficulty:
                self.dodge(random.choice([-1, 1]))
                self.ai_timer = react
                return

        # Guard if being punched close
        if player.punch_state and dist < 120 and random.random() < 0.3 * self.difficulty:
            self.guarding = True
            self.ai_timer = react
            return
        else:
            self.guarding = False

        if dist > 140:
            # Approach
            dx = -1 if self.x > player.x else 1
            dy = -1 if self.y > player.y else 1
            self.move(dx, dy)
            self.ai_timer = 2
        else:
            # Attack
            punches = ['jab_l', 'jab_r', 'cross_l', 'upper', 'body']
            weights = [3, 3, 2, 1, 1]
            if self.difficulty == 3:
                weights = [2, 2, 3, 2, 2]
            chosen = random.choices(punches, weights=weights)[0]
            if random.random() < 0.5:
                self.start_punch(chosen)
            self.ai_timer = react + random.randint(0, 20)


# ─── Game state ──────────────────────────────────────────────────────────────

class GameState:
    def __init__(self, difficulty=1):
        self.player  = Boxer(RING_CX - 180, RING_CY, RED, DARK_RED, "GRACZ", facing=1)
        self.ai      = AIBoxer(RING_CX + 180, RING_CY, difficulty)
        self.round   = 1
        self.max_rounds = 3
        self.round_time = 90 * FPS   # 90 seconds
        self.timer   = self.round_time
        self.paused  = False
        self.over    = False
        self.winner  = None

        # Mouse press tracking for cross
        self.lmb_down_since  = None
        self.rmb_down_since  = None
        self.CROSS_HOLD      = 0.28   # seconds to trigger cross

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                self.player.dodge(-1)
            elif event.key == pygame.K_e:
                self.player.dodge(1)
            elif event.key == pygame.K_c:
                self.player.start_punch('upper')
            elif event.key == pygame.K_r:
                self.player.start_punch('body')
            elif event.key == pygame.K_ESCAPE:
                self.paused = not self.paused

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                self.lmb_down_since = time.time()
            elif event.button == 3:
                self.rmb_down_since = time.time()

        if event.type == pygame.MOUSEBUTTONUP:
            now = time.time()
            if event.button == 1 and self.lmb_down_since is not None:
                held = now - self.lmb_down_since
                if held >= self.CROSS_HOLD:
                    self.player.start_punch('cross_l')
                else:
                    self.player.start_punch('jab_l')
                self.lmb_down_since = None
            elif event.button == 3 and self.rmb_down_since is not None:
                held = now - self.rmb_down_since
                if held >= self.CROSS_HOLD:
                    self.player.start_punch('cross_r')
                else:
                    self.player.start_punch('jab_r')
                self.rmb_down_since = None

    def update(self):
        if self.paused or self.over:
            return

        keys = pygame.key.get_pressed()
        dx = (1 if keys[pygame.K_d] else 0) - (1 if keys[pygame.K_a] else 0)
        dy = (1 if keys[pygame.K_s] else 0) - (1 if keys[pygame.K_w] else 0)
        self.player.guarding = keys[pygame.K_SPACE]

        if dx != 0 or dy != 0:
            self.player.move(dx, dy)

        self.player.update()
        self.ai.update()
        self.ai.ai_update(self.player)

        # Facing update
        if self.player.x < self.ai.x:
            self.player.facing =  1
            self.ai.facing     = -1
        else:
            self.player.facing = -1
            self.ai.facing     =  1

        # Hit detection
        self.player.try_hit(self.ai)
        self.ai.try_hit(self.player)

        # Timer
        self.timer -= 1
        if self.timer <= 0:
            self._end_round()

        # KO check
        if self.player.hp <= 0 and not self.player.knockdown:
            self.player.knockdown   = True
            self.player.knockdown_t = 240
        if self.ai.hp <= 0 and not self.ai.knockdown:
            self.ai.knockdown   = True
            self.ai.knockdown_t = 240

        if self.player.knockdown and self.player.knockdown_t <= 0:
            self._declare_winner("PRZECIWNIK")
        if self.ai.knockdown and self.ai.knockdown_t <= 0 and self.ai.hp <= 0:
            self._declare_winner("GRACZ")

    def _end_round(self):
        if self.round < self.max_rounds:
            self.round += 1
            self.timer  = self.round_time
            # Reset positions
            self.player.x, self.player.y = RING_CX - 180, RING_CY
            self.ai.x,    self.ai.y      = RING_CX + 180, RING_CY
            self.player.stun_timer = 0
            self.ai.stun_timer     = 0
        else:
            winner = "GRACZ" if self.player.hp > self.ai.hp else "PRZECIWNIK"
            self._declare_winner(winner)

    def _declare_winner(self, name):
        self.over   = True
        self.winner = name

    def draw(self, surf):
        surf.fill(BG_COLOR)
        draw_ring(surf)
        self.ai.draw(surf)
        self.player.draw(surf)
        update_particles(surf)
        update_floats(surf)
        self.player.draw_hud(surf, left_side=True)
        self.ai.draw_hud(surf, left_side=False)
        self._draw_timer(surf)
        if self.paused:
            self._draw_pause(surf)
        if self.over:
            self._draw_game_over(surf)

    def _draw_timer(self, surf):
        secs = self.timer // FPS
        mins = secs // 60
        s    = secs % 60
        txt  = font_med.render(f"RUNDA {self.round}  {mins}:{s:02d}", True, WHITE)
        surf.blit(txt, (WIDTH // 2 - txt.get_width() // 2, 14))

    def _draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        surf.blit(overlay, (0, 0))
        t = font_big.render("PAUZA", True, YELLOW)
        surf.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 50))
        t2 = font_small.render("ESC - kontynuuj", True, WHITE)
        surf.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 40))

    def _draw_game_over(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        surf.blit(overlay, (0, 0))
        col = GREEN if self.winner == "GRACZ" else RED
        t = font_big.render(f"{self.winner} WYGRYWA!", True, col)
        surf.blit(t, (WIDTH//2 - t.get_width()//2, HEIGHT//2 - 60))
        t2 = font_med.render("ENTER - menu główne", True, WHITE)
        surf.blit(t2, (WIDTH//2 - t2.get_width()//2, HEIGHT//2 + 30))


# ─── Menu ────────────────────────────────────────────────────────────────────

class Menu:
    OPTIONS     = ["NOWA GRA", "TRUDNOŚĆ", "STEROWANIE", "WYJŚCIE"]
    DIFFICULTY  = ["ŁATWY", "ŚREDNI", "TRUDNY"]

    def __init__(self):
        self.selected    = 0
        self.difficulty  = 0   # index into DIFFICULTY
        self.show_controls = False
        self.anim        = 0

    def handle_event(self, event):
        if self.show_controls:
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.show_controls = False
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.OPTIONS)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.OPTIONS)
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                return self._activate()
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._click(event.pos)
        return None

    def _activate(self):
        opt = self.OPTIONS[self.selected]
        if opt == "NOWA GRA":
            return ("start", self.difficulty + 1)
        if opt == "TRUDNOŚĆ":
            self.difficulty = (self.difficulty + 1) % 3
        if opt == "STEROWANIE":
            self.show_controls = True
        if opt == "WYJŚCIE":
            return ("quit",)
        return None

    def _click(self, pos):
        mx, my = pos
        start_y = HEIGHT // 2 - 60
        for i, opt in enumerate(self.OPTIONS):
            ry = start_y + i * 70
            if abs(my - ry - 20) < 30 and abs(mx - WIDTH // 2) < 200:
                self.selected = i
                return self._activate()
        return None

    def update(self):
        self.anim = (self.anim + 1) % 360

    def draw(self, surf):
        surf.fill(BG_COLOR)
        self._draw_bg(surf)

        if self.show_controls:
            self._draw_controls(surf)
            return

        # Title
        t = font_big.render("RING BOKS", True, YELLOW)
        surf.blit(t, (WIDTH//2 - t.get_width()//2, 80))
        t2 = font_small.render("64-BIT BOXING ARENA", True, ORANGE)
        surf.blit(t2, (WIDTH//2 - t2.get_width()//2, 160))

        # Options
        start_y = HEIGHT // 2 - 60
        for i, opt in enumerate(self.OPTIONS):
            label = opt
            if opt == "TRUDNOŚĆ":
                label = f"TRUDNOŚĆ: {self.DIFFICULTY[self.difficulty]}"
            selected = (i == self.selected)
            col = YELLOW if selected else GRAY
            glow_surf = font_med.render(label, True, col)
            x = WIDTH // 2 - glow_surf.get_width() // 2
            y = start_y + i * 70
            if selected:
                pygame.draw.rect(surf, (60, 40, 0),
                                 (x - 20, y - 6, glow_surf.get_width() + 40, 50),
                                 border_radius=10)
                pygame.draw.rect(surf, ORANGE,
                                 (x - 20, y - 6, glow_surf.get_width() + 40, 50),
                                 3, border_radius=10)
            surf.blit(glow_surf, (x, y))

        nav = font_tiny.render("↑↓ - wybór    ENTER/KLIK - potwierdź", True, DARK_GRAY)
        surf.blit(nav, (WIDTH//2 - nav.get_width()//2, HEIGHT - 40))

    def _draw_bg(self, surf):
        # Animated ropes in background
        a = self.anim
        for i in range(5):
            y = 100 + i * 120 + int(math.sin(math.radians(a + i * 40)) * 8)
            pygame.draw.line(surf, (60, 40, 10), (0, y), (WIDTH, y), 4)
        draw_ring(surf)
        # Darken overlay
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        surf.blit(ov, (0, 0))

    def _draw_controls(self, surf):
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 200))
        surf.blit(ov, (0, 0))

        t = font_med.render("STEROWANIE", True, YELLOW)
        surf.blit(t, (WIDTH//2 - t.get_width()//2, 60))

        controls = [
            ("W / S / A / D",          "Poruszanie się"),
            ("Q",                       "Unik w lewo"),
            ("E",                       "Unik w prawo"),
            ("LPM (krótko)",            "Lewy jab"),
            ("PPM (krótko)",            "Prawy jab"),
            ("LPM (przytrzymaj ~0.3s)", "Lewy cross"),
            ("PPM (przytrzymaj ~0.3s)", "Prawy cross"),
            ("C",                       "Podbródkowy (uppercut)"),
            ("R",                       "Niski jab w brzuch"),
            ("SPACJA",                  "Garda (blok)"),
            ("ESC",                     "Pauza"),
        ]

        for i, (key, desc) in enumerate(controls):
            y = 130 + i * 42
            k = font_small.render(key, True, ORANGE)
            d = font_small.render(desc, True, WHITE)
            surf.blit(k, (WIDTH//2 - 300, y))
            surf.blit(d, (WIDTH//2 + 20,  y))

        back = font_small.render("Naciśnij dowolny klawisz...", True, GRAY)
        surf.blit(back, (WIDTH//2 - back.get_width()//2, HEIGHT - 50))


# ─── Main loop ───────────────────────────────────────────────────────────────

def main():
    menu  = Menu()
    game  = None
    state = "menu"   # "menu" | "game"

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if state == "menu":
                result = menu.handle_event(event)
                if result:
                    if result[0] == "quit":
                        pygame.quit()
                        sys.exit()
                    elif result[0] == "start":
                        game  = GameState(difficulty=result[1])
                        state = "game"

            elif state == "game":
                game.handle_event(event)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN and game.over:
                        state = "menu"
                        game  = None

        if state == "menu":
            menu.update()
            menu.draw(screen)
        elif state == "game":
            game.update()
            game.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
