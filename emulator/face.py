"""The device itself, drawn to the dimensions in docs/UI.md and hardware/BOM.md."""

import math

import pygame

import layout

BODY_W, BODY_H = 76.0, 126.0
TOP_MARGIN = 16.0
SCREEN_W, SCREEN_H = 47.32, 81.12
BOARD_H = 96.5
GEAR_D = 12.0
LED_D = 9.0
LED_VISIBLE = 2 / 3
SIDE_GAP = (BODY_W - SCREEN_W) / 2

PX_PER_MM = 280 / SCREEN_W

SHELL = (44, 44, 48)
SHELL_EDGE = (72, 72, 78)
BEZEL = (26, 26, 29)
GEAR = (96, 96, 104)
GEAR_TOOTH = (58, 58, 64)
MIC = (30, 30, 34)
PAD = (60, 60, 66)
PAD_LIVE = (150, 120, 60)
LABEL = (128, 128, 138)


class Face:
    def __init__(self, scale=1.0):
        self.scale = scale
        self.px = PX_PER_MM * scale
        self.size = (round(BODY_W * self.px), round(BODY_H * self.px))
        board_top = TOP_MARGIN
        self.screen_rect = pygame.Rect(
            round((BODY_W - SCREEN_W) / 2 * self.px),
            round((board_top + (BOARD_H - SCREEN_H) / 2) * self.px),
            round(SCREEN_W * self.px),
            round(SCREEN_H * self.px),
        )
        self.leds = layout.ROWS

    def mm(self, v):
        return round(v * self.px)

    def led_centres(self):
        """Three round lenses a side, low on the face, level with the menu rows."""
        out = []
        radius = self.mm(LED_D / 2)
        for i in range(self.leds):
            cy = round(self.screen_rect.top + self.screen_rect.height * layout.row_fraction(i))
            for side, cx in (
                (-1, self.screen_rect.left - self.mm(SIDE_GAP * 0.42)),
                (1, self.screen_rect.right + self.mm(SIDE_GAP * 0.42)),
            ):
                out.append((i, (cx, cy), radius, side))
        return out

    def gear_centres(self):
        inset = self.mm(GEAR_D / 2 + 2)
        return [(inset, inset), (self.size[0] - inset, inset)]

    def draw(self, surface, origin, panel_surface, rows, touch_live, font):
        x0, y0 = origin
        body = pygame.Rect(x0, y0, *self.size)
        pygame.draw.rect(surface, SHELL, body, border_radius=self.mm(4))
        pygame.draw.rect(surface, SHELL_EDGE, body, width=2, border_radius=self.mm(4))

        for index, (cx, cy), radius, side in self.led_centres():
            centre = (x0 + cx, y0 + cy)
            r, g, b, _w = rows[index % len(rows)]
            seen = round(radius * 2 * LED_VISIBLE)
            clip = pygame.Rect(0, 0, seen, radius * 2)
            clip.centery = centre[1]
            clip.left = centre[0] + radius - seen if side < 0 else centre[0] - radius
            previous = surface.get_clip()
            surface.set_clip(clip)
            pygame.draw.circle(surface, (24, 24, 28), centre, radius)
            pygame.draw.circle(surface, (r // 5 + 22, g // 5 + 22, b // 5 + 24), centre, radius - 2)
            if r or g or b:
                pygame.draw.circle(surface, (r, g, b), centre, radius - 3)
            surface.set_clip(previous)
            cut = clip.left if side < 0 else clip.right
            pygame.draw.line(surface, SHELL_EDGE, (cut, clip.top), (cut, clip.bottom), 2)

        screen = self.screen_rect.move(x0, y0)
        pygame.draw.rect(surface, BEZEL, screen.inflate(self.mm(1.5), self.mm(1.5)))
        surface.blit(pygame.transform.smoothscale(panel_surface, screen.size), screen)

        for cx, cy in self.gear_centres():
            centre = (x0 + cx, y0 + cy)
            radius = self.mm(GEAR_D / 2)
            pygame.draw.circle(surface, GEAR_TOOTH, centre, radius)
            pygame.draw.circle(surface, GEAR, centre, radius - 3)
            for k in range(12):
                a = k * math.pi / 6
                pygame.draw.line(
                    surface,
                    GEAR_TOOTH,
                    (centre[0] + int((radius - 4) * math.cos(a)), centre[1] + int((radius - 4) * math.sin(a))),
                    (centre[0] + int(radius * math.cos(a)), centre[1] + int(radius * math.sin(a))),
                    2,
                )

        slot_y = y0 + self.mm(4)
        for i in range(7):
            sx = x0 + self.size[0] // 2 - self.mm(7) + i * self.mm(2.2)
            pygame.draw.rect(surface, MIC, pygame.Rect(sx, slot_y, self.mm(0.9), self.mm(5)))

        pad = pygame.Rect(0, 0, self.mm(26), self.mm(12))
        pad.center = (x0 + self.size[0] // 2, y0 + self.mm(BODY_H - 11))
        pygame.draw.rect(surface, PAD_LIVE if touch_live else PAD, pad, border_radius=self.mm(1.5))

        for text, pos in (
            ("Z  back", (x0 + self.mm(1.5), y0 + self.mm(GEAR_D + 3))),
            ("X  ok", (x0 + self.mm(1.5), y0 + self.mm(GEAR_D + 7))),
            ("< >  turn", (x0 + self.size[0] - self.mm(13), y0 + self.mm(GEAR_D + 3))),
            ("space", (pad.right + self.mm(3), pad.centery - self.mm(1.4))),
        ):
            surface.blit(font.render(text, True, LABEL), pos)
