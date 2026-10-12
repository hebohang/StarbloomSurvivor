"""Generate the complete deterministic Starbloom Survivor icon catalog.

The artwork is built only from Pillow primitives.  It deliberately avoids
fonts, downloaded imagery, wiki artwork, and generative-image services so the
result can be reproduced and audited from this repository alone.
"""

from __future__ import print_function

import argparse
import hashlib
import io
import json
import os
import sys
from collections import namedtuple
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw


GENERATOR_VERSION = 3
ICON_SIZE = 96
SUPERSAMPLE = 4
WORK_SIZE = ICON_SIZE * SUPERSAMPLE
OUTLINE = "#43235F"
CREAM = "#FFF3CF"
WHITE = "#FFFFFF"
INK = "#382052"
MANIFEST_ASSET_PATH = "Assets/UI/Icons/Survivor/manifest.json"

try:
    RESAMPLE_LANCZOS = Image.Resampling.LANCZOS
except AttributeError:  # Pillow < 9.1
    RESAMPLE_LANCZOS = Image.LANCZOS


Design = namedtuple(
    "Design",
    "category icon_id glyph primary secondary accent variant",
)


def D(category, icon_id, glyph, primary, secondary, accent, variant=0):
    return Design(category, icon_id, glyph, primary, secondary, accent, variant)


def icon_asset_path(design):
    # SurvivorCatalogWorld._boss intentionally reuses _enemy, so Boss icons are
    # catalogued beside Enemies even though the manifest keeps their logical
    # category distinct.
    directory = "Enemies" if design.category == "Bosses" else design.category
    return "Assets/UI/Icons/Survivor/%s/%s.png" % (
        directory,
        design.icon_id,
    )


DESIGNS = (
    # Characters: model-inspired silhouettes rather than letter badges.
    D("Characters", "starpaw", "character_cat_star", "#6BB7FF", "#FFF3CF", "#FFD45C", 0),
    D("Characters", "peachy", "character_pig_heart", "#FF9FB3", "#FFD5C8", "#FF6F88", 1),
    D("Characters", "mossling", "character_cactus_sprout", "#74D695", "#B8EA7A", "#FFD45C", 2),
    D("Characters", "snowbean", "character_panda_snow", "#F7F3E8", "#6D5B88", "#75DDF0", 3),
    D("Characters", "azura", "character_penguin_petal", "#5F92D9", "#F8F4E7", "#F39AC9", 4),
    D("Characters", "honeybun", "character_bee_honey", "#FFD45C", "#6A4C76", "#74DCE0", 5),
    D("Characters", "mushmellow", "character_mushroom_spore", "#F195C9", "#FFF0D0", "#81D79B", 6),
    D("Characters", "boolet", "character_ghost_echo", "#B79CFF", "#E9E5FF", "#69DCE2", 7),
    D("Characters", "crabble", "character_crab_coral", "#FF806F", "#FFB46E", "#6CDAD2", 8),
    D("Characters", "cosmobob", "character_alien_prism", "#78D7B0", "#AA8CF7", "#FFD45C", 9),

    # Weapons.
    D("Weapons", "ring", "weapon_ripple_disc", "#59DDE0", "#A7F4E7", "#FFFFFF", 1),
    D("Weapons", "fireball", "weapon_chibi_flame", "#FF734F", "#FFB43F", "#FFF17A", 2),
    D("Weapons", "moonblade", "weapon_crescent_blade", "#A98CFF", "#E7E1FF", "#6ACEE8", 3),
    D("Weapons", "bubble", "weapon_bubble_chain", "#55CBEA", "#A6F3F1", "#F6A5DB", 4),
    D("Weapons", "aura", "weapon_butterfly_aura", "#65D6D2", "#B59BFF", "#FFF1A0", 7),
    D("Weapons", "dagger", "weapon_winged_dagger", "#F8F2E4", "#79BCEB", "#FFD45C", 8),
    D("Weapons", "starwheel", "weapon_returning_starwheel", "#FFD45C", "#74D9D4", "#FFF4C7", 9),
    D("Weapons", "petalstorm", "weapon_petal_nova", "#F38FBE", "#FFB69F", "#FFD45C", 10),
    D("Weapons", "comet", "weapon_comet_choir", "#62B6F0", "#73DFCF", "#FFF0A0", 11),
    D("Weapons", "honeyneedle", "weapon_honey_needle", "#FFD34E", "#8A5A47", "#6EDBD3", 12),
    D("Weapons", "sporecap", "weapon_spore_cap", "#E98EC7", "#FFF0CF", "#79D59B", 13),
    D("Weapons", "phantombell", "weapon_phantom_bell", "#AA8CF7", "#E7E1FF", "#6EDBDC", 14),
    D("Weapons", "coralanchor", "weapon_coral_anchor", "#FF806F", "#FFB56E", "#62D4D2", 15),
    D("Weapons", "prismorbit", "weapon_prism_orbit", "#86D8D0", "#B18DF5", "#FFD45C", 16),
    D("Weapons", "acornmortar", "weapon_acorn_mortar", "#B9784B", "#8FD072", "#FFD45C", 17),
    D("Weapons", "frostorb", "weapon_frost_orb", "#A8E8F5", "#6EBCEB", "#FFFFFF", 18),
    D("Weapons", "gravityyoyo", "weapon_gravity_yoyo", "#805FD1", "#F39AC9", "#74D9D4", 19),
    D("Weapons", "rainbowrail", "weapon_rainbow_rail", "#6EBCEA", "#FF8E96", "#FFD45C", 20),

    # Tomes: a shared book language with a unique outer accent and central rune.
    D("Tomes", "magnet", "tome_magnet", "#5BCFDB", "#FFF0CB", "#FF726D", 0),
    D("Tomes", "vitality", "tome_heart", "#FF8F9B", "#FFF0CB", "#FFD45C", 1),
    D("Tomes", "guard", "tome_shield", "#63B7CC", "#FFF0CB", "#72D8AF", 2),
    D("Tomes", "might", "tome_might_burst", "#F2B34C", "#FFF0CB", "#FF786E", 3),
    D("Tomes", "haste", "tome_clock", "#6DABE9", "#FFF0CB", "#B08EF6", 4),
    D("Tomes", "reach", "tome_arrows", "#63CDBF", "#FFF0CB", "#FFD45C", 5),
    D("Tomes", "fortune", "tome_clover", "#F0B83E", "#FFF0CB", "#71D39A", 6),
    D("Tomes", "growth", "tome_sprout", "#8ACD72", "#FFF0CB", "#B68FF5", 7),
    D("Tomes", "quantity", "tome_triple_star", "#E88FC5", "#FFF0CB", "#FFD45C", 8),
    D("Tomes", "velocity", "tome_comet", "#66B9EC", "#FFF0CB", "#74DCCD", 9),
    D("Tomes", "duration", "tome_long_moon", "#8F7BE4", "#FFF0CB", "#6DCEE2", 10),
    D("Tomes", "recovery", "tome_recovery_cross", "#6ED3A0", "#FFF0CB", "#F08FB5", 11),
    D("Tomes", "thorns", "tome_thorn_vine", "#75B96E", "#FFF0CB", "#FF8071", 12),
    D("Tomes", "greed", "tome_coin_sun", "#F1B93C", "#FFF0CB", "#8FD171", 13),
    D("Tomes", "status", "tome_status_flask", "#9A7FE8", "#FFF0CB", "#6EDAD3", 14),
    D("Tomes", "curse", "tome_curse_eye", "#7454A8", "#FFF0CB", "#F06B91", 15),

    # Permanent PowerUps use bold toy-like badges with unique silhouettes.
    D("PowerUps", "meta_might", "powerup_star_fist", "#F3B642", "#FF7D70", "#FFF0A0", 0),
    D("PowerUps", "meta_health", "powerup_heart_crown", "#FF8798", "#FFD2D8", "#FFD45C", 1),
    D("PowerUps", "meta_recovery", "powerup_healing_orbit", "#69D3A1", "#FFF0D2", "#F292BC", 2),
    D("PowerUps", "meta_move", "powerup_winged_boot", "#69B9EC", "#E9F7FF", "#FFD45C", 3),
    D("PowerUps", "meta_magnet", "powerup_star_magnet", "#65BCE8", "#FF7A73", "#FFD45C", 4),
    D("PowerUps", "meta_growth", "powerup_rising_sprout", "#7DCE78", "#C7EC83", "#B38FF5", 5),
    D("PowerUps", "meta_luck", "powerup_star_clover", "#72D39A", "#FFF0A0", "#F19AC8", 6),
    D("PowerUps", "meta_greed", "powerup_coin_pouch", "#F1B83F", "#B97A4A", "#76D5C9", 7),
    D("PowerUps", "meta_reroll", "powerup_reroll_dice", "#9C82EB", "#73D6D0", "#FFD45C", 8),
    D("PowerUps", "meta_skip", "powerup_comet_skip", "#68B9EA", "#79DBCD", "#FF8A92", 9),
    D("PowerUps", "meta_banish", "powerup_sealed_portal", "#7655AA", "#F08FB8", "#FFD45C", 10),
    D("PowerUps", "meta_revive", "powerup_rekindled_bloom", "#70D5A2", "#FF8D82", "#FFD45C", 11),
    D("PowerUps", "meta_weapon_slots", "powerup_weapon_slot_satchel", "#8F78E8", "#69D7D0", "#FFD45C", 12),

    # Trinkets.
    D("Trinkets", "prism_lens", "trinket_prism_lens", "#79D7D4", "#A98CFF", "#FFD45C", 0),
    D("Trinkets", "popcorn_kernel", "trinket_popcorn", "#FFF0A0", "#FF8C78", "#75D8D1", 1),
    D("Trinkets", "sticky_honey", "trinket_honey_jar", "#FFD34E", "#B97A47", "#74D9D4", 2),
    D("Trinkets", "echo_shell", "trinket_echo_shell", "#F0A1C8", "#A98CF5", "#6EDAD3", 3),
    D("Trinkets", "lucky_ribbon", "trinket_lucky_ribbon", "#FF8396", "#FFD45C", "#7AD8B1", 4),
    D("Trinkets", "tiny_magnet", "trinket_tiny_magnet", "#66B8E7", "#FF7D72", "#FFD45C", 5),
    D("Trinkets", "glass_star", "trinket_glass_star", "#A8EAF3", "#FFFFFF", "#B396F7", 6),
    D("Trinkets", "marshmallow_shield", "trinket_marshmallow_shield", "#FFF0DF", "#F5A4C7", "#6DD4CD", 7),
    D("Trinkets", "boss_bell", "trinket_boss_bell", "#E8A941", "#7A55A8", "#FF756E", 8),
    D("Trinkets", "bloom_battery", "trinket_bloom_battery", "#6ED5A4", "#FFD45C", "#F38FBE", 9),
    D("Trinkets", "comet_tail", "trinket_comet_tail", "#66B8EA", "#75DBCF", "#FFF0A0", 10),
    D("Trinkets", "friendship_pin", "trinket_friendship_pin", "#F194C1", "#72D8CF", "#FFD45C", 11),

    # Weapon evolutions use visibly richer compound emblems.
    D("Evolutions", "supernovachoir", "evolution_supernova_choir", "#FFD45C", "#69BCEB", "#F18FC5", 0),
    D("Evolutions", "royalbubblecade", "evolution_royal_bubble", "#6DDDE0", "#B39AF8", "#FFD45C", 1),
    D("Evolutions", "nebulanetwork", "evolution_nebula_network", "#E9E6FF", "#7CBCEB", "#F18FC4", 2),
    D("Evolutions", "galaxygarden", "evolution_galaxy_garden", "#F18FC2", "#7AD6AC", "#FFD45C", 4),
    D("Evolutions", "royalbeehive", "evolution_royal_beehive", "#FFD34E", "#A96D43", "#72DAD2", 5),
    D("Evolutions", "myceliumcarnival", "evolution_mycelium_carnival", "#EE91C7", "#7CD5A2", "#FFD45C", 6),
    D("Evolutions", "midnightencore", "evolution_midnight_encore", "#977DE8", "#E9E4FF", "#69D7D9", 7),
    D("Evolutions", "tidalfortress", "evolution_tidal_fortress", "#64CBD6", "#FF8D79", "#FFD45C", 8),
    D("Evolutions", "friendshipspectrum", "evolution_friendship_spectrum", "#76D8D0", "#B18EF5", "#FF8FAF", 9),

    # Enemies communicate role as well as species.
    D("Enemies", "green_blob", "enemy_green_chaser", "#7BD47E", "#B9EA76", "#FFD45C", 0),
    D("Enemies", "pink_blob", "enemy_pink_flanker", "#F28CB5", "#FFB38F", "#75D8D1", 1),
    D("Enemies", "spiky_blob", "enemy_spiky_guard", "#72B86C", "#A6D66D", "#FF8A73", 2),
    D("Enemies", "orc_bruiser", "enemy_orc_bruiser", "#8BC46D", "#A66B46", "#FFD45C", 3),
    D("Enemies", "yeti_zoner", "enemy_yeti_zoner", "#D9EDF0", "#6FB9E6", "#A98CF5", 4),
    D("Enemies", "alien_charger", "enemy_alien_charger", "#76D7AC", "#A98CF5", "#FF826F", 5),
    D("Enemies", "bee_ranger", "enemy_bee_ranger", "#FFD34E", "#6B4A75", "#6EDAD2", 6),
    D("Enemies", "mushroom_lobber", "enemy_mushroom_lobber", "#EB8FC5", "#FFF0CF", "#78D19B", 7),
    D("Enemies", "ghost_ambusher", "enemy_ghost_ambusher", "#AB91F4", "#E7E2FF", "#68D7D9", 8),
    D("Enemies", "crab_guard", "enemy_crab_guard", "#FF806F", "#FFB36C", "#66D2D0", 9),
    D("Enemies", "bomb_spore", "enemy_bomb_spore", "#A46BC1", "#F18EBE", "#FFD45C", 10),
    D("Enemies", "alien_commander", "enemy_alien_commander", "#67CF9F", "#9276DC", "#FFD45C", 11),

    # Bosses.
    D("Bosses", "yeti_colossus", "boss_yeti_colossus", "#DDEFF2", "#70B8E5", "#B18FF5", 0),
    D("Bosses", "orc_warlord", "boss_orc_warlord", "#88BC69", "#9A6042", "#FFD45C", 1),
    D("Bosses", "azure_demon", "boss_azure_demon", "#527FCF", "#8D69D4", "#66D8D2", 2),
    D("Bosses", "mushroom_monarch", "boss_mushroom_monarch", "#E787C2", "#FFF0C9", "#FFD45C", 3),
    D("Bosses", "star_dragon", "boss_star_dragon", "#72D0A8", "#8D72DC", "#FFD45C", 4),
)


CATEGORY_COUNTS = {
    "Characters": 10,
    "Weapons": 18,
    "Tomes": 16,
    "PowerUps": 13,
    "Trinkets": 12,
    "Evolutions": 9,
    "Enemies": 12,
    "Bosses": 5,
}


def rgba(value, alpha=255):
    if isinstance(value, tuple):
        if len(value) == 4:
            return value
        return value + (alpha,)
    red, green, blue = ImageColor.getrgb(value)
    return red, green, blue, alpha


class Painter(object):
    def __init__(self, image):
        self.image = image
        self.draw = ImageDraw.Draw(image)

    @staticmethod
    def _box(box):
        return tuple(int(round(value * SUPERSAMPLE)) for value in box)

    @staticmethod
    def _points(points):
        return [
            (int(round(x * SUPERSAMPLE)), int(round(y * SUPERSAMPLE)))
            for x, y in points
        ]

    def ellipse(self, box, fill, outline=None, width=0):
        self.draw.ellipse(
            self._box(box),
            fill=rgba(fill) if fill is not None else None,
            outline=rgba(outline) if outline is not None else None,
            width=int(round(width * SUPERSAMPLE)),
        )

    def rectangle(self, box, fill, outline=None, width=0):
        self.draw.rectangle(
            self._box(box),
            fill=rgba(fill) if fill is not None else None,
            outline=rgba(outline) if outline is not None else None,
            width=int(round(width * SUPERSAMPLE)),
        )

    def rounded(self, box, radius, fill, outline=None, width=0):
        self.draw.rounded_rectangle(
            self._box(box),
            radius=int(round(radius * SUPERSAMPLE)),
            fill=rgba(fill) if fill is not None else None,
            outline=rgba(outline) if outline is not None else None,
            width=int(round(width * SUPERSAMPLE)),
        )

    def polygon(self, points, fill, outline=None, width=0):
        scaled = self._points(points)
        self.draw.polygon(scaled, fill=rgba(fill) if fill is not None else None)
        if outline is not None and width > 0:
            self.draw.line(
                scaled + [scaled[0]],
                fill=rgba(outline),
                width=int(round(width * SUPERSAMPLE)),
                joint="curve",
            )

    def line(self, points, fill, width, joint="curve"):
        self.draw.line(
            self._points(points),
            fill=rgba(fill),
            width=int(round(width * SUPERSAMPLE)),
            joint=joint,
        )

    def arc(self, box, start, end, fill, width):
        self.draw.arc(
            self._box(box),
            start=start,
            end=end,
            fill=rgba(fill),
            width=int(round(width * SUPERSAMPLE)),
        )


def regular_points(cx, cy, radius, count, rotation=-90.0):
    import math
    return [
        (
            cx + math.cos(math.radians(rotation + index * 360.0 / count)) * radius,
            cy + math.sin(math.radians(rotation + index * 360.0 / count)) * radius,
        )
        for index in range(count)
    ]


def star_points(cx, cy, outer, inner, points=5, rotation=-90.0):
    import math
    result = []
    for index in range(points * 2):
        angle = math.radians(rotation + index * 180.0 / points)
        radius = outer if index % 2 == 0 else inner
        result.append((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
    return result


def shadow(painter, box=(19, 76, 77, 85)):
    painter.ellipse(box, (44, 23, 70, 72))


def glint(painter, cx, cy, radius=4.0, color=WHITE):
    painter.polygon(
        ((cx, cy - radius), (cx + radius * 0.34, cy - radius * 0.34),
         (cx + radius, cy), (cx + radius * 0.34, cy + radius * 0.34),
         (cx, cy + radius), (cx - radius * 0.34, cy + radius * 0.34),
         (cx - radius, cy), (cx - radius * 0.34, cy - radius * 0.34)),
        color,
    )


def face(painter, left=(39, 50), right=(57, 50), mouth_y=61, happy=True):
    for x, y in (left, right):
        painter.ellipse((x - 3.2, y - 4.2, x + 3.2, y + 4.2), INK)
        painter.ellipse((x - 1.7, y - 2.8, x - 0.2, y - 1.2), WHITE)
    if happy:
        painter.arc((43, mouth_y - 5, 53, mouth_y + 5), 12, 168, INK, 2.2)
    else:
        painter.arc((43, mouth_y, 53, mouth_y + 8), 195, 345, INK, 2.2)


def heart(painter, cx, cy, size, fill, outline=OUTLINE):
    painter.polygon(
        ((cx - size, cy - size * 0.20), (cx, cy + size),
         (cx + size, cy - size * 0.20), (cx + size * 0.72, cy - size * 0.72),
         (cx, cy - size * 0.30), (cx - size * 0.72, cy - size * 0.72)),
        fill, outline, 3.0,
    )


def draw_character(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    shadow(p)
    icon_id = spec.icon_id
    if icon_id == "starpaw":
        p.polygon(((21, 42), (25, 18), (41, 33)), primary, OUTLINE, 4)
        p.polygon(((75, 42), (71, 18), (55, 33)), primary, OUTLINE, 4)
        p.ellipse((22, 27, 74, 80), primary, OUTLINE, 4)
        p.ellipse((35, 54, 61, 74), secondary)
        p.polygon(star_points(48, 35, 8, 3.6), accent, OUTLINE, 2)
        face(p, mouth_y=62)
    elif icon_id == "peachy":
        p.ellipse((13, 29, 34, 50), primary, OUTLINE, 4)
        p.ellipse((62, 29, 83, 50), primary, OUTLINE, 4)
        p.ellipse((19, 25, 77, 80), primary, OUTLINE, 4)
        p.ellipse((32, 53, 64, 73), secondary, OUTLINE, 3)
        p.ellipse((39, 59, 43, 65), INK)
        p.ellipse((53, 59, 57, 65), INK)
        face(p, (37, 46), (59, 46), 70)
        heart(p, 70, 29, 6, accent, OUTLINE)
    elif icon_id == "mossling":
        p.rounded((28, 17, 68, 82), 17, primary, OUTLINE, 4)
        p.rounded((12, 40, 34, 60), 9, primary, OUTLINE, 4)
        p.rounded((62, 31, 84, 51), 9, primary, OUTLINE, 4)
        p.line(((24, 31), (24, 45)), secondary, 3)
        p.line(((72, 24), (72, 36)), secondary, 3)
        p.polygon(((46, 19), (51, 8), (56, 21)), accent, OUTLINE, 2.5)
        face(p, (40, 49), (57, 49), 61)
    elif icon_id == "snowbean":
        p.ellipse((14, 17, 39, 42), secondary, OUTLINE, 4)
        p.ellipse((57, 17, 82, 42), secondary, OUTLINE, 4)
        p.ellipse((20, 23, 76, 81), primary, OUTLINE, 4)
        p.ellipse((30, 39, 44, 57), secondary)
        p.ellipse((52, 39, 66, 57), secondary)
        face(p, (37, 48), (59, 48), 62)
        glint(p, 48, 29, 5, accent)
    elif icon_id == "azura":
        p.ellipse((20, 13, 76, 84), primary, OUTLINE, 4)
        p.ellipse((30, 34, 66, 78), secondary)
        p.polygon(((43, 51), (53, 51), (48, 58)), accent, OUTLINE, 2)
        p.ellipse((34, 36, 41, 45), INK)
        p.ellipse((55, 36, 62, 45), INK)
        p.polygon(((22, 51), (10, 63), (27, 67)), primary, OUTLINE, 3)
        p.polygon(((74, 51), (86, 63), (69, 67)), primary, OUTLINE, 3)
        p.polygon(star_points(68, 25, 6, 2.8), accent, OUTLINE, 2)
    elif icon_id == "honeybun":
        p.ellipse((13, 31, 41, 65), secondary, OUTLINE, 3)
        p.ellipse((55, 31, 83, 65), secondary, OUTLINE, 3)
        p.ellipse((28, 22, 68, 80), primary, OUTLINE, 4)
        p.rectangle((31, 43, 65, 51), secondary)
        p.rectangle((31, 59, 65, 67), secondary)
        p.line(((39, 25), (31, 13)), OUTLINE, 3)
        p.line(((57, 25), (65, 13)), OUTLINE, 3)
        p.ellipse((27, 10, 34, 17), accent, OUTLINE, 2)
        p.ellipse((62, 10, 69, 17), accent, OUTLINE, 2)
        face(p, (41, 35), (55, 35), 46)
    elif icon_id == "mushmellow":
        p.rounded((35, 48, 61, 82), 10, secondary, OUTLINE, 4)
        p.ellipse((14, 20, 82, 62), primary, OUTLINE, 4)
        p.ellipse((26, 30, 40, 42), accent)
        p.ellipse((58, 27, 70, 38), secondary)
        face(p, (42, 61), (55, 61), 72)
        p.ellipse((75, 18, 82, 25), accent, OUTLINE, 2)
    elif icon_id == "boolet":
        p.polygon(((20, 74), (20, 44), (25, 25), (38, 16), (55, 18),
                   (70, 30), (76, 48), (76, 74), (65, 66), (56, 77),
                   (46, 67), (35, 77)), primary, OUTLINE, 4)
        p.ellipse((31, 44, 43, 57), INK)
        p.ellipse((55, 42, 66, 55), INK)
        p.arc((37, 55, 58, 69), 20, 160, accent, 3)
        p.arc((12, 24, 84, 84), 208, 318, secondary, 3)
    elif icon_id == "crabble":
        p.ellipse((24, 32, 72, 76), primary, OUTLINE, 4)
        p.ellipse((8, 23, 34, 49), primary, OUTLINE, 4)
        p.ellipse((62, 23, 88, 49), primary, OUTLINE, 4)
        p.line(((31, 35), (25, 19)), OUTLINE, 3)
        p.line(((65, 35), (71, 19)), OUTLINE, 3)
        p.ellipse((21, 14, 29, 22), accent, OUTLINE, 2)
        p.ellipse((67, 14, 75, 22), accent, OUTLINE, 2)
        face(p, (40, 48), (56, 48), 61)
        p.line(((32, 70), (23, 82)), secondary, 4)
        p.line(((64, 70), (73, 82)), secondary, 4)
    elif icon_id == "cosmobob":
        p.polygon(((48, 9), (53, 23), (48, 30), (43, 23)), accent, OUTLINE, 2.5)
        p.ellipse((19, 22, 77, 79), primary, OUTLINE, 4)
        p.polygon(((24, 43), (33, 27), (63, 27), (72, 43), (64, 68),
                   (48, 78), (32, 68)), primary, OUTLINE, 3)
        p.ellipse((29, 41, 44, 55), secondary, OUTLINE, 2)
        p.ellipse((52, 41, 67, 55), secondary, OUTLINE, 2)
        p.ellipse((34, 45, 41, 52), INK)
        p.ellipse((55, 45, 62, 52), INK)
        p.arc((39, 57, 57, 69), 20, 160, INK, 2.5)
    else:
        raise ValueError("Unknown character icon: " + icon_id)


def crown(p, cx, cy, width, fill, accent=WHITE):
    half = width * 0.5
    p.polygon(
        ((cx - half, cy + 8), (cx - half + 2, cy - 6),
         (cx - width * 0.20, cy + 1), (cx, cy - 10),
         (cx + width * 0.20, cy + 1), (cx + half - 2, cy - 6),
         (cx + half, cy + 8)),
        fill, OUTLINE, 3,
    )
    p.line(((cx - half + 3, cy + 4), (cx + half - 3, cy + 4)), accent, 2)


def draw_weapon(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    icon_id = spec.icon_id
    shadow(p)
    if icon_id == "thunder":
        for box in ((17, 50, 43, 76), (34, 43, 63, 76), (54, 51, 79, 76)):
            p.ellipse(box, secondary, OUTLINE, 3)
        p.polygon(((52, 10), (30, 48), (45, 48), (37, 83),
                   (70, 39), (53, 39)), primary, OUTLINE, 4)
        glint(p, 61, 20, 4, accent)
    elif icon_id == "ring":
        p.ellipse((13, 22, 83, 82), secondary, OUTLINE, 4)
        p.ellipse((24, 32, 72, 72), (0, 0, 0, 0), primary, 5)
        p.ellipse((35, 41, 61, 64), (0, 0, 0, 0), OUTLINE, 3)
        p.ellipse((43, 48, 53, 58), accent, OUTLINE, 2)
        glint(p, 73, 24, 4)
    elif icon_id == "fireball":
        p.polygon(((47, 8), (60, 25), (70, 21), (68, 42), (80, 45),
                   (69, 69), (50, 83), (28, 71), (18, 49), (31, 42),
                   (29, 25), (43, 34)), primary, OUTLINE, 4)
        p.polygon(((49, 33), (61, 47), (58, 67), (47, 75), (35, 64),
                   (35, 49)), secondary, OUTLINE, 2.5)
        p.ellipse((43, 51, 54, 66), accent)
        glint(p, 61, 18, 3)
    elif icon_id == "moonblade":
        p.polygon(((18, 70), (30, 37), (55, 14), (76, 15), (59, 31),
                   (71, 43), (50, 46), (32, 76)), primary, OUTLINE, 4)
        p.polygon(((23, 72), (32, 77), (25, 86), (16, 79)), accent, OUTLINE, 2)
        p.arc((30, 16, 78, 61), 200, 330, secondary, 4)
        glint(p, 72, 20, 4)
    elif icon_id == "bubble":
        for box, fill in (((15, 44, 45, 76), primary), ((36, 24, 69, 59), secondary),
                          ((60, 13, 84, 39), accent)):
            p.ellipse(box, fill, OUTLINE, 3)
        glint(p, 29, 54, 4)
        glint(p, 49, 34, 3)
        p.ellipse((70, 20, 76, 26), WHITE)
    elif icon_id == "tornado":
        p.arc((14, 12, 82, 48), 5, 175, primary, 8)
        p.arc((23, 28, 75, 61), 5, 175, secondary, 7)
        p.arc((31, 45, 67, 75), 5, 175, primary, 6)
        p.polygon(((39, 66), (59, 66), (53, 85), (45, 85)), accent, OUTLINE, 3)
        glint(p, 72, 29, 3)
    elif icon_id == "starfall":
        for x, top, bottom in ((28, 15, 42), (49, 8, 49), (70, 19, 45)):
            p.line(((x, top), (x, bottom)), accent, 4)
        p.polygon(star_points(28, 50, 12, 5), primary, OUTLINE, 3)
        p.polygon(star_points(50, 59, 16, 7), secondary, OUTLINE, 3)
        p.polygon(star_points(70, 51, 11, 4.5), primary, OUTLINE, 3)
        p.ellipse((29, 78, 69, 85), (255, 212, 92, 120))
    elif icon_id == "aura":
        p.ellipse((25, 25, 71, 73), primary, OUTLINE, 4)
        p.ellipse((37, 37, 59, 61), accent, OUTLINE, 2)
        p.ellipse((9, 33, 37, 59), secondary, OUTLINE, 3)
        p.ellipse((59, 33, 87, 59), secondary, OUTLINE, 3)
        p.arc((13, 11, 83, 87), 205, 335, accent, 3)
        glint(p, 48, 49, 6)
    elif icon_id == "dagger":
        p.polygon(((52, 10), (64, 19), (48, 62), (38, 67), (35, 56)),
                  primary, OUTLINE, 4)
        p.line(((31, 58), (55, 72)), accent, 6)
        p.polygon(((38, 66), (28, 84), (20, 79), (33, 62)), secondary, OUTLINE, 3)
        p.polygon(((26, 44), (10, 37), (22, 55)), secondary, OUTLINE, 2.5)
        p.polygon(((65, 49), (83, 44), (69, 60)), secondary, OUTLINE, 2.5)
        glint(p, 63, 18, 3)
    elif icon_id == "starwheel":
        p.polygon(star_points(48, 48, 35, 18, 8), primary, OUTLINE, 4)
        p.ellipse((31, 31, 65, 65), secondary, OUTLINE, 3)
        p.ellipse((42, 42, 54, 54), accent, OUTLINE, 2)
        p.arc((9, 8, 87, 88), 190, 312, secondary, 3)
        p.polygon(((80, 64), (88, 69), (79, 73)), secondary, OUTLINE, 2)
    elif icon_id == "petalstorm":
        petals = (((48, 14), (39, 39), (48, 47), (57, 39)),
                  ((76, 31), (54, 41), (53, 52), (69, 57)),
                  ((71, 69), (54, 55), (44, 61), (48, 80)),
                  ((25, 70), (40, 55), (35, 45), (15, 51)),
                  ((21, 29), (39, 41), (47, 34), (39, 15)))
        for index, points in enumerate(petals):
            p.polygon(points, primary if index % 2 == 0 else secondary, OUTLINE, 3)
        p.ellipse((38, 38, 58, 58), accent, OUTLINE, 3)
        glint(p, 48, 48, 5)
    elif icon_id == "comet":
        p.polygon(((13, 76), (34, 42), (50, 28), (44, 58), (69, 45),
                   (54, 66)), secondary, OUTLINE, 4)
        p.ellipse((46, 18, 82, 54), primary, OUTLINE, 4)
        p.polygon(star_points(64, 36, 11, 5), accent, OUTLINE, 2.5)
        p.line(((19, 65), (8, 75)), primary, 4)
        glint(p, 80, 18, 3)
    elif icon_id == "honeyneedle":
        p.polygon(((67, 12), (76, 22), (42, 65), (31, 70), (35, 58)),
                  primary, OUTLINE, 4)
        p.line(((42, 55), (53, 65)), secondary, 5)
        p.polygon(((30, 46), (13, 39), (25, 57)), accent, OUTLINE, 3)
        p.polygon(((47, 69), (59, 84), (38, 78)), accent, OUTLINE, 3)
        p.ellipse((60, 61, 75, 79), primary, OUTLINE, 2)
    elif icon_id == "sporecap":
        p.rounded((39, 48, 58, 82), 7, secondary, OUTLINE, 4)
        p.ellipse((14, 20, 82, 59), primary, OUTLINE, 4)
        p.ellipse((25, 31, 38, 42), accent)
        p.ellipse((57, 29, 70, 41), secondary)
        for x, y in ((20, 67), (72, 64), (67, 80)):
            p.ellipse((x - 3, y - 3, x + 3, y + 3), accent, OUTLINE, 1.5)
    elif icon_id == "phantombell":
        p.polygon(((31, 62), (34, 30), (42, 18), (54, 18), (63, 30),
                   (66, 62), (73, 71), (23, 71)), primary, OUTLINE, 4)
        p.ellipse((42, 66, 54, 81), accent, OUTLINE, 2.5)
        p.arc((10, 24, 40, 66), 100, 260, secondary, 3)
        p.arc((56, 24, 86, 66), 280, 80, secondary, 3)
        glint(p, 48, 34, 4)
    elif icon_id == "coralanchor":
        p.line(((48, 16), (48, 69)), primary, 8)
        p.ellipse((39, 10, 57, 28), secondary, OUTLINE, 3)
        p.arc((18, 38, 78, 84), 12, 168, primary, 7)
        p.polygon(((19, 57), (14, 77), (30, 70)), primary, OUTLINE, 3)
        p.polygon(((77, 57), (82, 77), (66, 70)), primary, OUTLINE, 3)
        p.line(((55, 48), (68, 35), (72, 25)), accent, 4)
        p.line(((41, 53), (30, 42), (25, 34)), accent, 4)
    elif icon_id == "prismorbit":
        p.polygon(((48, 15), (69, 35), (62, 65), (48, 80), (32, 64), (27, 35)),
                  primary, OUTLINE, 4)
        p.polygon(((48, 15), (48, 79), (62, 65), (69, 35)), secondary, OUTLINE, 2)
        p.arc((8, 24, 88, 73), 188, 352, accent, 3)
        p.ellipse((12, 43, 22, 53), accent, OUTLINE, 2)
        p.ellipse((75, 42, 85, 52), accent, OUTLINE, 2)
        glint(p, 40, 30, 3)
    elif icon_id == "acornmortar":
        p.ellipse((24, 28, 66, 78), primary, OUTLINE, 4)
        p.polygon(((21, 35), (30, 18), (61, 17), (70, 35)), secondary, OUTLINE, 4)
        p.line(((48, 19), (58, 8)), accent, 4)
        p.arc((51, 7, 88, 44), 205, 330, accent, 3)
        p.polygon(star_points(77, 24, 8, 3.5), accent, OUTLINE, 2)
        p.line(((35, 47), (55, 64)), secondary, 3)
    elif icon_id == "frostorb":
        p.ellipse((17, 16, 79, 80), primary, OUTLINE, 4)
        p.ellipse((27, 26, 69, 70), secondary, OUTLINE, 2)
        for angle_points in (((48, 30), (48, 66)), ((30, 48), (66, 48)),
                             ((35, 35), (61, 61)), ((61, 35), (35, 61))):
            p.line(angle_points, WHITE, 3)
        p.polygon(star_points(48, 48, 12, 5, 6), accent, OUTLINE, 2)
        glint(p, 65, 29, 4)
    elif icon_id == "gravityyoyo":
        p.line(((27, 15), (54, 41)), accent, 4)
        p.ellipse((34, 34, 77, 78), primary, OUTLINE, 4)
        p.ellipse((47, 47, 64, 65), secondary, OUTLINE, 3)
        p.arc((11, 31, 72, 87), 80, 235, accent, 3)
        p.polygon(((14, 62), (7, 70), (18, 72)), accent, OUTLINE, 2)
        glint(p, 61, 44, 3)
    elif icon_id == "rainbowrail":
        p.polygon(((13, 58), (23, 36), (57, 30), (70, 40), (63, 58),
                   (34, 62), (27, 79), (15, 74)), primary, OUTLINE, 4)
        p.rectangle((55, 37, 82, 50), secondary, OUTLINE, 3)
        p.line(((70, 42), (90, 42)), "#FF7B7B", 4)
        p.line(((70, 47), (90, 47)), accent, 4)
        p.line(((69, 52), (88, 52)), "#6EDAD3", 4)
        glint(p, 34, 44, 3)
    else:
        raise ValueError("Unknown weapon icon: " + icon_id)


def draw_tome_symbol(p, spec):
    cx, cy = 51, 48
    primary, accent = spec.primary, spec.accent
    icon_id = spec.icon_id
    if icon_id == "magnet":
        p.arc((34, 33, 68, 67), 0, 180, primary, 8)
        p.rectangle((32, 47, 40, 64), "#FF776F", OUTLINE, 2)
        p.rectangle((62, 47, 70, 64), "#6CB9E8", OUTLINE, 2)
    elif icon_id == "vitality":
        heart(p, cx, cy, 15, primary, OUTLINE)
        glint(p, 58, 39, 3)
    elif icon_id == "guard":
        p.polygon(((51, 29), (69, 37), (66, 58), (51, 70), (36, 58), (33, 37)),
                  primary, OUTLINE, 3)
        p.line(((51, 35), (51, 63)), accent, 2.5)
    elif icon_id == "might":
        p.polygon(star_points(cx, cy, 20, 10, 8), primary, OUTLINE, 3)
        p.polygon(((45, 39), (57, 39), (60, 50), (55, 62), (43, 61), (40, 49)),
                  accent, OUTLINE, 2)
    elif icon_id == "haste":
        p.ellipse((34, 31, 68, 66), primary, OUTLINE, 3)
        p.line(((51, 48), (51, 36)), accent, 3)
        p.line(((51, 48), (61, 53)), accent, 3)
        p.ellipse((37, 24, 47, 32), primary, OUTLINE, 2)
        p.ellipse((57, 24, 67, 32), primary, OUTLINE, 2)
    elif icon_id == "reach":
        p.line(((34, 48), (68, 48)), primary, 5)
        p.line(((51, 31), (51, 65)), accent, 5)
        for points in (((34, 48), (42, 42), (42, 54)), ((68, 48), (60, 42), (60, 54)),
                       ((51, 31), (45, 39), (57, 39)), ((51, 65), (45, 57), (57, 57))):
            p.polygon(points, primary if points[0][1] == 48 else accent, OUTLINE, 1.5)
    elif icon_id == "fortune":
        for box in ((36, 29, 52, 47), (50, 29, 66, 47), (36, 44, 52, 62), (50, 44, 66, 62)):
            p.ellipse(box, primary, OUTLINE, 2)
        p.line(((51, 55), (58, 69)), accent, 3)
    elif icon_id == "growth":
        p.line(((51, 67), (51, 37)), primary, 4)
        p.ellipse((31, 34, 51, 49), primary, OUTLINE, 2.5)
        p.ellipse((51, 27, 71, 44), accent, OUTLINE, 2.5)
        p.arc((36, 49, 66, 72), 180, 360, OUTLINE, 2)
    elif icon_id == "quantity":
        p.polygon(star_points(39, 48, 10, 4.5), primary, OUTLINE, 2)
        p.polygon(star_points(57, 39, 11, 5), accent, OUTLINE, 2)
        p.polygon(star_points(59, 58, 9, 4), primary, OUTLINE, 2)
    elif icon_id == "velocity":
        p.polygon(((31, 66), (43, 42), (58, 31), (51, 54)), primary, OUTLINE, 3)
        p.ellipse((51, 25, 69, 43), accent, OUTLINE, 2)
        p.line(((32, 51), (22, 58)), primary, 3)
        p.line(((38, 40), (27, 43)), accent, 3)
    elif icon_id == "duration":
        p.ellipse((34, 28, 68, 66), primary, OUTLINE, 3)
        p.ellipse((46, 23, 70, 61), CREAM)
        p.line(((33, 68), (69, 68)), accent, 3)
        glint(p, 38, 36, 3)
    elif icon_id == "recovery":
        p.rounded((43, 28, 59, 68), 3, primary, OUTLINE, 2.5)
        p.rounded((31, 40, 71, 56), 3, primary, OUTLINE, 2.5)
        heart(p, 68, 31, 5, accent, OUTLINE)
    elif icon_id == "thorns":
        p.line(((34, 66), (42, 53), (37, 43), (51, 34), (64, 29)), primary, 4)
        for x, y, direction in ((40, 54, -1), (40, 42, 1), (51, 35, -1), (60, 31, 1)):
            p.polygon(((x, y), (x + direction * 9, y - 5), (x + direction * 5, y + 4)),
                      accent, OUTLINE, 1.5)
    elif icon_id == "greed":
        p.ellipse((33, 30, 69, 67), primary, OUTLINE, 3)
        p.polygon(star_points(51, 49, 13, 6, 8), accent, OUTLINE, 2)
        p.arc((26, 23, 76, 74), 200, 330, primary, 3)
    elif icon_id == "status":
        p.polygon(((43, 28), (59, 28), (57, 40), (68, 63), (61, 69),
                   (41, 69), (34, 63), (45, 40)), primary, OUTLINE, 3)
        p.polygon(((38, 57), (64, 57), (61, 66), (41, 66)), accent, OUTLINE, 2)
        p.ellipse((58, 34, 65, 41), accent, OUTLINE, 1.5)
    elif icon_id == "curse":
        p.polygon(((51, 27), (65, 36), (70, 48), (63, 62), (51, 69),
                   (39, 62), (32, 48), (37, 35)), primary, OUTLINE, 3)
        p.ellipse((39, 40, 63, 57), accent, OUTLINE, 2)
        p.ellipse((47, 43, 55, 55), INK)
        glint(p, 51, 47, 2, WHITE)
    else:
        raise ValueError("Unknown Tome icon: " + icon_id)


def draw_tome(p, spec):
    shadow(p, (16, 77, 82, 87))
    variant = spec.variant % 4
    x0 = 15 + (variant % 2)
    y0 = 13 + (variant // 2)
    p.rounded((x0, y0, 81, 82), 10, spec.secondary, OUTLINE, 4)
    p.rounded((22, 17, 76, 77), 7, CREAM, OUTLINE, 2)
    p.rectangle((18, 20, 29, 75), spec.primary, OUTLINE, 2)
    if variant in (0, 2):
        p.polygon(((65, 15), (78, 15), (78, 29), (70, 25), (65, 29)),
                  spec.accent, OUTLINE, 2)
    else:
        p.polygon(((35, 75), (47, 75), (47, 87), (41, 82), (35, 87)),
                  spec.accent, OUTLINE, 2)
    draw_tome_symbol(p, spec)
    glint(p, 69, 69, 2.8)


def draw_power_up(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    icon_id = spec.icon_id
    shadow(p, (14, 77, 82, 88))
    if icon_id == "meta_might":
        p.polygon(star_points(48, 46, 35, 22, 10), secondary, OUTLINE, 4)
        p.rounded((30, 34, 66, 71), 9, primary, OUTLINE, 3)
        for box in ((34, 29, 43, 47), (43, 27, 52, 46), (52, 29, 61, 47)):
            p.rounded(box, 3, accent, OUTLINE, 2)
        p.line(((33, 55), (63, 55)), OUTLINE, 3)
        p.polygon(((48, 38), (55, 50), (50, 50), (50, 65),
                   (46, 65), (46, 50), (41, 50)), accent, OUTLINE, 2)
        glint(p, 74, 22, 3)
    elif icon_id == "meta_health":
        heart(p, 48, 50, 28, primary, OUTLINE)
        crown(p, 48, 22, 34, accent, WHITE)
        p.rounded((44, 39, 52, 66), 2, secondary, OUTLINE, 1.5)
        p.rounded((35, 48, 61, 57), 2, secondary, OUTLINE, 1.5)
        glint(p, 69, 38, 3)
    elif icon_id == "meta_recovery":
        p.ellipse((24, 24, 72, 72), secondary, OUTLINE, 3)
        p.rounded((43, 33, 53, 63), 3, primary, OUTLINE, 2)
        p.rounded((33, 43, 63, 53), 3, primary, OUTLINE, 2)
        p.arc((12, 11, 84, 85), 205, 500, accent, 7)
        p.polygon(((18, 24), (8, 35), (25, 37)), accent, OUTLINE, 2)
        heart(p, 69, 25, 6, primary, OUTLINE)
        glint(p, 73, 63, 3)
    elif icon_id == "meta_move":
        p.polygon(((37, 24), (55, 24), (57, 53), (75, 62),
                   (70, 77), (33, 77), (26, 67), (37, 54)),
                  primary, OUTLINE, 4)
        p.polygon(((38, 34), (18, 24), (27, 43), (10, 46),
                   (33, 58)), secondary, OUTLINE, 3)
        p.polygon(((59, 54), (80, 39), (75, 58), (88, 62),
                   (65, 69)), secondary, OUTLINE, 3)
        p.line(((37, 48), (54, 48)), accent, 4)
        p.line(((36, 59), (52, 59)), accent, 4)
        glint(p, 60, 22, 3)
    elif icon_id == "meta_magnet":
        p.arc((16, 15, 80, 80), 0, 180, primary, 15)
        p.rounded((15, 48, 33, 78), 4, secondary, OUTLINE, 3)
        p.rounded((63, 48, 81, 78), 4, "#FF7A73", OUTLINE, 3)
        p.polygon(star_points(48, 43, 14, 6), accent, OUTLINE, 2.5)
        p.arc((27, 28, 69, 69), 205, 335, secondary, 3)
        glint(p, 73, 25, 3)
    elif icon_id == "meta_growth":
        p.rounded((28, 62, 68, 80), 6, secondary, OUTLINE, 4)
        p.line(((48, 68), (48, 30)), primary, 5)
        p.ellipse((21, 32, 49, 51), primary, OUTLINE, 3)
        p.ellipse((48, 22, 77, 43), secondary, OUTLINE, 3)
        p.polygon(((48, 13), (59, 29), (52, 29), (52, 46),
                   (44, 46), (44, 29), (37, 29)), accent, OUTLINE, 2.5)
        p.line(((36, 72), (60, 72)), accent, 3)
        glint(p, 73, 53, 3)
    elif icon_id == "meta_luck":
        for box in ((23, 20, 50, 48), (46, 20, 73, 48),
                    (23, 44, 50, 72), (46, 44, 73, 72)):
            p.ellipse(box, primary, OUTLINE, 3)
        p.ellipse((39, 37, 58, 57), secondary, OUTLINE, 2)
        p.polygon(star_points(48, 47, 9, 4), accent, OUTLINE, 2)
        p.line(((48, 60), (61, 82)), secondary, 5)
        p.arc((12, 12, 84, 84), 195, 325, accent, 3)
        glint(p, 75, 21, 3)
    elif icon_id == "meta_greed":
        p.polygon(((30, 31), (39, 20), (57, 20), (66, 31),
                   (76, 61), (66, 80), (30, 80), (20, 61)),
                  secondary, OUTLINE, 4)
        p.line(((31, 32), (65, 32)), accent, 5)
        p.ellipse((31, 42, 65, 75), primary, OUTLINE, 3)
        p.polygon(star_points(48, 58, 12, 5, 8), accent, OUTLINE, 2)
        p.ellipse((69, 18, 84, 34), primary, OUTLINE, 2)
        glint(p, 75, 24, 3)
    elif icon_id == "meta_reroll":
        p.arc((12, 12, 84, 84), 195, 355, primary, 8)
        p.polygon(((75, 19), (88, 24), (78, 34)), primary, OUTLINE, 2.5)
        p.arc((12, 12, 84, 84), 15, 175, secondary, 8)
        p.polygon(((21, 77), (8, 72), (18, 62)), secondary, OUTLINE, 2.5)
        p.rounded((31, 30, 65, 65), 8, CREAM, OUTLINE, 4)
        for x, y in ((40, 40), (56, 40), (48, 48), (40, 56), (56, 56)):
            p.ellipse((x - 3, y - 3, x + 3, y + 3), accent, OUTLINE, 1)
        glint(p, 70, 54, 3)
    elif icon_id == "meta_skip":
        p.polygon(((14, 27), (39, 48), (14, 69)), primary, OUTLINE, 4)
        p.polygon(((38, 27), (63, 48), (38, 69)), secondary, OUTLINE, 4)
        p.polygon(star_points(73, 48, 15, 7), accent, OUTLINE, 3)
        p.line(((17, 77), (57, 77)), secondary, 4)
        p.line(((10, 18), (47, 18)), primary, 3)
        glint(p, 79, 33, 3)
    elif icon_id == "meta_banish":
        p.ellipse((16, 14, 80, 82), primary, OUTLINE, 5)
        p.ellipse((28, 27, 68, 69), secondary, OUTLINE, 3)
        p.ellipse((39, 38, 57, 58), INK, OUTLINE, 2)
        p.polygon(star_points(48, 48, 8, 3.5, 6), accent, OUTLINE, 1.5)
        p.line(((22, 75), (75, 20)), "#FF8B88", 8)
        p.line(((25, 76), (78, 21)), CREAM, 2)
        glint(p, 75, 67, 3)
    elif icon_id == "meta_revive":
        p.arc((23, 8, 73, 31), 185, 355, accent, 5)
        p.polygon(((48, 17), (62, 36), (57, 49), (72, 51),
                   (63, 73), (48, 86), (32, 73), (24, 52),
                   (39, 48), (34, 36)), secondary, OUTLINE, 4)
        p.polygon(((48, 37), (58, 53), (54, 69), (48, 77),
                   (39, 68), (39, 54)), primary, OUTLINE, 2.5)
        p.ellipse((38, 43, 49, 55), accent, OUTLINE, 2)
        p.ellipse((49, 40, 60, 52), accent, OUTLINE, 2)
        p.line(((48, 66), (48, 47)), accent, 3)
        glint(p, 70, 29, 3)
    elif icon_id == "meta_weapon_slots":
        p.rounded((12, 22, 84, 80), 13, secondary, OUTLINE, 4)
        p.line(((24, 25), (31, 14), (65, 14), (72, 25)), OUTLINE, 5)
        for index, x0 in enumerate((20, 39, 58)):
            fill = primary if index != 1 else CREAM
            p.rounded((x0, 34, x0 + 18, 68), 5, fill, OUTLINE, 2.5)
            p.polygon(
                star_points(x0 + 9, 51, 6, 2.8),
                accent if index != 2 else WHITE,
                OUTLINE,
                1.4,
            )
        p.rounded((37, 72, 59, 84), 5, accent, OUTLINE, 2.5)
        p.line(((43, 78), (53, 78)), WHITE, 2.2)
        glint(p, 76, 24, 3)
    else:
        raise ValueError("Unknown PowerUp icon: " + icon_id)


def draw_trinket(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    icon_id = spec.icon_id
    shadow(p)
    if icon_id == "prism_lens":
        p.line(((30, 69), (18, 84)), secondary, 8)
        p.ellipse((24, 18, 76, 70), primary, OUTLINE, 4)
        p.polygon(((50, 25), (68, 41), (58, 62), (36, 59), (30, 40)),
                  secondary, OUTLINE, 3)
        p.line(((50, 25), (50, 58)), accent, 2)
        glint(p, 61, 30, 4)
    elif icon_id == "popcorn_kernel":
        p.polygon(((25, 46), (71, 46), (65, 82), (31, 82)), secondary, OUTLINE, 4)
        p.polygon(((31, 48), (40, 82), (48, 48), (56, 82), (65, 48)),
                  primary, OUTLINE, 2)
        for box in ((19, 25, 42, 48), (34, 17, 58, 46), (53, 24, 77, 49), (31, 29, 65, 54)):
            p.ellipse(box, primary, OUTLINE, 2.5)
        glint(p, 56, 24, 3, accent)
    elif icon_id == "sticky_honey":
        p.rounded((24, 25, 72, 80), 10, secondary, OUTLINE, 4)
        p.rectangle((31, 16, 65, 31), primary, OUTLINE, 3)
        p.polygon(((24, 48), (72, 48), (72, 73), (24, 73)), primary, OUTLINE, 2)
        p.polygon(((48, 42), (58, 56), (55, 68), (48, 73), (41, 68), (38, 56)),
                  accent, OUTLINE, 2.5)
        glint(p, 61, 37, 3)
    elif icon_id == "echo_shell":
        p.ellipse((15, 18, 80, 82), primary, OUTLINE, 4)
        p.arc((28, 30, 68, 69), 20, 355, secondary, 5)
        p.arc((38, 39, 60, 61), 20, 330, accent, 4)
        p.polygon(((20, 62), (8, 69), (25, 73)), secondary, OUTLINE, 2.5)
        p.arc((69, 20, 91, 53), 280, 80, accent, 3)
    elif icon_id == "lucky_ribbon":
        p.ellipse((37, 28, 59, 51), accent, OUTLINE, 3)
        p.polygon(((42, 42), (16, 28), (19, 58)), primary, OUTLINE, 4)
        p.polygon(((54, 42), (80, 28), (77, 58)), primary, OUTLINE, 4)
        p.polygon(((42, 48), (32, 83), (48, 69)), secondary, OUTLINE, 3)
        p.polygon(((54, 48), (64, 83), (48, 69)), secondary, OUTLINE, 3)
        p.polygon(star_points(48, 41, 7, 3), accent, OUTLINE, 2)
    elif icon_id == "tiny_magnet":
        p.arc((20, 17, 76, 75), 0, 180, primary, 13)
        p.rectangle((18, 48, 33, 75), secondary, OUTLINE, 3)
        p.rectangle((63, 48, 78, 75), "#FF786F", OUTLINE, 3)
        p.ellipse((39, 35, 57, 53), accent, OUTLINE, 2)
        glint(p, 48, 44, 4)
    elif icon_id == "glass_star":
        p.polygon(star_points(48, 48, 36, 16), primary, OUTLINE, 4)
        p.polygon(((48, 14), (48, 70), (68, 60)), secondary, OUTLINE, 2)
        p.line(((32, 35), (64, 59)), WHITE, 3)
        glint(p, 58, 31, 5)
    elif icon_id == "marshmallow_shield":
        p.polygon(((48, 14), (76, 25), (73, 55), (61, 73), (48, 83),
                   (35, 73), (23, 55), (20, 25)), primary, OUTLINE, 4)
        p.rounded((31, 29, 65, 64), 13, secondary, OUTLINE, 3)
        p.ellipse((39, 40, 45, 47), INK)
        p.ellipse((53, 40, 59, 47), INK)
        p.arc((41, 48, 57, 59), 15, 165, INK, 2)
        glint(p, 66, 24, 3, accent)
    elif icon_id == "boss_bell":
        crown(p, 48, 22, 35, secondary, accent)
        p.polygon(((29, 67), (34, 36), (42, 26), (54, 26), (63, 36),
                   (68, 67), (76, 74), (20, 74)), primary, OUTLINE, 4)
        p.ellipse((41, 68, 55, 84), accent, OUTLINE, 2.5)
        p.line(((22, 45), (12, 39)), secondary, 3)
        p.line(((74, 45), (84, 39)), secondary, 3)
    elif icon_id == "bloom_battery":
        p.rounded((25, 27, 71, 79), 8, primary, OUTLINE, 4)
        p.rectangle((39, 17, 57, 30), secondary, OUTLINE, 3)
        for points in (((48, 33), (40, 48), (48, 54), (56, 48)),
                       ((48, 54), (40, 67), (48, 74), (56, 67))):
            p.polygon(points, accent, OUTLINE, 2)
        p.line(((48, 42), (48, 66)), secondary, 3)
        glint(p, 65, 35, 3)
    elif icon_id == "comet_tail":
        p.polygon(((10, 76), (31, 42), (56, 25), (45, 58), (71, 48),
                   (55, 70), (29, 82)), secondary, OUTLINE, 4)
        p.ellipse((52, 16, 82, 47), primary, OUTLINE, 4)
        p.polygon(star_points(67, 31, 9, 4), accent, OUTLINE, 2)
        p.line(((23, 61), (11, 65)), primary, 3)
        glint(p, 79, 18, 3)
    elif icon_id == "friendship_pin":
        p.ellipse((19, 18, 77, 77), primary, OUTLINE, 4)
        p.polygon(((35, 77), (48, 88), (61, 77)), secondary, OUTLINE, 3)
        heart(p, 48, 47, 17, secondary, OUTLINE)
        p.ellipse((28, 35, 40, 48), accent, OUTLINE, 2)
        p.ellipse((56, 35, 68, 48), accent, OUTLINE, 2)
        glint(p, 48, 47, 4)
    else:
        raise ValueError("Unknown Trinket icon: " + icon_id)


def draw_evolution(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    icon_id = spec.icon_id
    shadow(p, (13, 76, 83, 87))
    if icon_id == "supernovachoir":
        p.polygon(star_points(48, 48, 34, 15, 7), primary, OUTLINE, 4)
        p.polygon(star_points(48, 48, 18, 8), accent, OUTLINE, 2.5)
        for x, y in ((18, 27), (78, 27), (74, 72)):
            p.polygon(star_points(x, y, 7, 3), secondary, OUTLINE, 2)
        p.arc((9, 10, 87, 88), 190, 345, secondary, 3)
    elif icon_id == "royalbubblecade":
        p.ellipse((18, 29, 78, 83), primary, OUTLINE, 4)
        p.ellipse((31, 42, 65, 73), secondary, OUTLINE, 2)
        crown(p, 48, 25, 43, accent, WHITE)
        for box in ((8, 47, 25, 64), (72, 43, 89, 60), (67, 67, 82, 82)):
            p.ellipse(box, secondary, OUTLINE, 2)
        glint(p, 61, 45, 4)
    elif icon_id == "nebulanetwork":
        p.line(((24, 29), (48, 53), (74, 27), (64, 73), (28, 72), (24, 29)),
               secondary, 4)
        for cx, cy, angle in ((24, 29, 0), (74, 27, 0), (64, 73, 0), (28, 72, 0)):
            p.polygon(((cx, cy - 13), (cx + 6, cy - 3), (cx + 2, cy + 10),
                       (cx - 5, cy + 5)), primary, OUTLINE, 2.5)
        p.polygon(star_points(48, 52, 10, 4), accent, OUTLINE, 2)
    elif icon_id == "storybooktempest":
        p.polygon(((12, 34), (43, 28), (48, 39), (53, 28), (84, 34),
                   (76, 72), (51, 77), (48, 67), (45, 77), (20, 72)),
                  secondary, OUTLINE, 4)
        p.arc((28, 20, 70, 51), 5, 175, primary, 6)
        p.arc((34, 34, 65, 60), 5, 175, accent, 5)
        p.polygon(((42, 55), (58, 55), (53, 81), (46, 81)), primary, OUTLINE, 3)
    elif icon_id == "galaxygarden":
        for cx, cy in ((48, 24), (70, 42), (62, 68), (34, 69), (25, 43)):
            p.ellipse((cx - 11, cy - 7, cx + 11, cy + 7), primary, OUTLINE, 2.5)
        p.ellipse((38, 38, 58, 58), accent, OUTLINE, 3)
        p.arc((10, 11, 86, 87), 195, 338, secondary, 3)
        p.ellipse((11, 43, 21, 53), secondary, OUTLINE, 2)
        p.ellipse((76, 41, 86, 51), secondary, OUTLINE, 2)
        glint(p, 48, 48, 5)
    elif icon_id == "royalbeehive":
        crown(p, 48, 20, 42, accent, WHITE)
        p.polygon(((30, 31), (66, 31), (76, 48), (69, 75), (48, 84),
                   (27, 75), (20, 48)), primary, OUTLINE, 4)
        for y in (43, 55, 67):
            p.line(((27, y), (69, y)), secondary, 4)
        p.ellipse((41, 59, 55, 72), INK, OUTLINE, 2)
        p.ellipse((9, 42, 29, 63), secondary, OUTLINE, 2.5)
        p.ellipse((67, 42, 87, 63), secondary, OUTLINE, 2.5)
    elif icon_id == "myceliumcarnival":
        for cx, cy, scale in ((27, 58, 0.75), (49, 48, 1.0), (71, 59, 0.72)):
            p.rounded((cx - 5 * scale, cy, cx + 5 * scale, cy + 21 * scale),
                      3, CREAM, OUTLINE, 2)
            p.ellipse((cx - 15 * scale, cy - 12 * scale, cx + 15 * scale, cy + 6 * scale),
                      primary if cx != 49 else secondary, OUTLINE, 2.5)
        p.arc((14, 13, 82, 84), 192, 345, accent, 3)
        for x, y in ((17, 35), (48, 14), (80, 35)):
            p.ellipse((x - 4, y - 4, x + 4, y + 4), accent, OUTLINE, 2)
    elif icon_id == "midnightencore":
        p.ellipse((21, 14, 70, 68), primary, OUTLINE, 4)
        p.ellipse((39, 8, 76, 58), (0, 0, 0, 0))
        p.polygon(((30, 69), (34, 38), (42, 29), (54, 29), (62, 38),
                   (66, 69), (72, 76), (24, 76)), secondary, OUTLINE, 4)
        p.ellipse((42, 70, 54, 84), accent, OUTLINE, 2)
        p.arc((6, 29, 37, 73), 95, 260, accent, 3)
        glint(p, 70, 19, 4)
    elif icon_id == "tidalfortress":
        p.polygon(((48, 12), (78, 25), (74, 57), (62, 75), (48, 85),
                   (34, 75), (22, 57), (18, 25)), primary, OUTLINE, 4)
        p.line(((48, 28), (48, 70)), secondary, 6)
        p.ellipse((40, 21, 56, 37), accent, OUTLINE, 2.5)
        p.arc((29, 38, 67, 76), 15, 165, secondary, 5)
        p.line(((29, 55), (20, 45)), accent, 3)
        p.line(((67, 55), (76, 45)), accent, 3)
    elif icon_id == "friendshipspectrum":
        p.polygon(((48, 14), (70, 35), (61, 67), (48, 81), (33, 67), (26, 35)),
                  primary, OUTLINE, 4)
        p.polygon(((48, 14), (48, 80), (61, 67), (70, 35)), secondary, OUTLINE, 2)
        p.arc((8, 15, 88, 82), 190, 350, accent, 4)
        heart(p, 17, 50, 7, "#FF8FAF", OUTLINE)
        heart(p, 80, 48, 7, "#FFD45C", OUTLINE)
        glint(p, 40, 30, 3)
    else:
        raise ValueError("Unknown Evolution icon: " + icon_id)


def draw_enemy(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    icon_id = spec.icon_id
    shadow(p)
    if icon_id == "green_blob":
        p.polygon(((17, 68), (20, 42), (31, 24), (48, 18), (65, 24),
                   (77, 43), (80, 68), (69, 79), (57, 74), (48, 82),
                   (37, 74), (27, 80)), primary, OUTLINE, 4)
        face(p, (38, 48), (58, 48), 61)
        glint(p, 68, 33, 3, accent)
    elif icon_id == "pink_blob":
        p.polygon(((11, 61), (24, 48), (19, 30), (39, 21), (61, 25),
                   (77, 41), (82, 62), (68, 76), (42, 78), (25, 70)),
                  primary, OUTLINE, 4)
        p.polygon(((14, 52), (5, 38), (26, 43)), accent, OUTLINE, 3)
        p.line(((61, 18), (78, 12)), secondary, 4)
        p.polygon(((82, 11), (73, 7), (76, 18)), secondary, OUTLINE, 2)
        face(p, (43, 46), (62, 45), 59)
    elif icon_id == "spiky_blob":
        p.polygon(star_points(48, 49, 39, 28, 11), primary, OUTLINE, 4)
        p.ellipse((24, 27, 72, 75), secondary, OUTLINE, 3)
        face(p, (38, 48), (58, 48), 62, happy=False)
        p.line(((35, 39), (43, 42)), OUTLINE, 2.5)
        p.line(((53, 42), (61, 39)), OUTLINE, 2.5)
    elif icon_id == "orc_bruiser":
        p.polygon(((20, 36), (32, 18), (64, 18), (77, 36), (72, 70),
                   (58, 82), (38, 82), (24, 70)), primary, OUTLINE, 4)
        p.polygon(((20, 35), (12, 25), (28, 29)), secondary, OUTLINE, 3)
        p.polygon(((76, 35), (84, 25), (68, 29)), secondary, OUTLINE, 3)
        p.ellipse((31, 43, 43, 54), INK)
        p.ellipse((53, 43, 65, 54), INK)
        p.polygon(((29, 60), (40, 67), (35, 75)), CREAM, OUTLINE, 2)
        p.polygon(((67, 60), (56, 67), (61, 75)), CREAM, OUTLINE, 2)
        p.line(((68, 21), (83, 72)), secondary, 6)
        p.rectangle((72, 12, 87, 31), accent, OUTLINE, 3)
    elif icon_id == "yeti_zoner":
        p.polygon(((23, 33), (12, 20), (31, 23), (39, 14), (48, 23),
                   (57, 14), (65, 23), (84, 20), (73, 34), (78, 67),
                   (62, 82), (34, 82), (18, 67)), primary, OUTLINE, 4)
        p.ellipse((28, 33, 68, 72), secondary, OUTLINE, 3)
        face(p, (40, 48), (56, 48), 61, happy=False)
        p.polygon(star_points(48, 26, 8, 3.5, 6), accent, OUTLINE, 2)
        p.arc((7, 49, 89, 90), 190, 350, accent, 3)
    elif icon_id == "alien_charger":
        p.polygon(((48, 15), (72, 30), (78, 56), (65, 76), (48, 84),
                   (31, 76), (18, 56), (24, 30)), primary, OUTLINE, 4)
        p.ellipse((28, 37, 44, 55), secondary, OUTLINE, 2)
        p.ellipse((52, 37, 68, 55), secondary, OUTLINE, 2)
        p.line(((12, 23), (33, 23)), accent, 5)
        p.polygon(((38, 23), (28, 14), (28, 32)), accent, OUTLINE, 2)
        p.line(((20, 66), (7, 71)), accent, 4)
        glint(p, 48, 66, 3)
    elif icon_id == "bee_ranger":
        p.ellipse((11, 31, 38, 61), accent, OUTLINE, 3)
        p.ellipse((58, 31, 85, 61), accent, OUTLINE, 3)
        p.ellipse((28, 20, 68, 80), primary, OUTLINE, 4)
        p.rectangle((31, 43, 65, 51), secondary)
        p.rectangle((31, 59, 65, 67), secondary)
        p.line(((64, 31), (87, 18)), "#FF8A73", 4)
        p.polygon(((88, 18), (76, 17), (84, 28)), "#FF8A73", OUTLINE, 2)
        face(p, (41, 35), (55, 35), 46, happy=False)
    elif icon_id == "mushroom_lobber":
        p.rounded((38, 49, 59, 82), 8, secondary, OUTLINE, 4)
        p.ellipse((14, 20, 82, 60), primary, OUTLINE, 4)
        p.ellipse((26, 31, 39, 42), accent)
        p.ellipse((58, 29, 70, 40), secondary)
        face(p, (42, 62), (55, 62), 72, happy=False)
        p.arc((56, 5, 92, 45), 205, 340, accent, 3)
        p.ellipse((78, 15, 88, 25), accent, OUTLINE, 2)
    elif icon_id == "ghost_ambusher":
        p.polygon(((19, 75), (19, 43), (27, 24), (43, 15), (61, 20),
                   (74, 36), (77, 75), (65, 66), (56, 79), (45, 67),
                   (34, 79)), primary, OUTLINE, 4)
        p.ellipse((31, 39, 44, 55), INK)
        p.ellipse((55, 37, 68, 53), INK)
        p.line(((21, 24), (74, 69)), accent, 4)
        p.polygon(((75, 69), (64, 68), (73, 58)), accent, OUTLINE, 2)
        p.arc((5, 31, 36, 75), 95, 260, secondary, 3)
    elif icon_id == "crab_guard":
        p.ellipse((24, 31, 72, 75), primary, OUTLINE, 4)
        p.ellipse((7, 21, 34, 49), primary, OUTLINE, 4)
        p.ellipse((62, 21, 89, 49), primary, OUTLINE, 4)
        p.polygon(((48, 34), (69, 42), (65, 66), (48, 79), (31, 66), (27, 42)),
                  accent, OUTLINE, 3)
        p.line(((48, 41), (48, 70)), secondary, 2)
        p.ellipse((38, 28, 44, 35), INK)
        p.ellipse((52, 28, 58, 35), INK)
    elif icon_id == "bomb_spore":
        p.rounded((39, 50, 58, 82), 7, secondary, OUTLINE, 4)
        p.ellipse((17, 24, 79, 62), primary, OUTLINE, 4)
        p.ellipse((29, 34, 40, 44), accent)
        p.line(((60, 27), (70, 14), (80, 18)), OUTLINE, 3)
        p.polygon(star_points(82, 16, 7, 3), accent, OUTLINE, 2)
        face(p, (42, 63), (55, 63), 73, happy=False)
    elif icon_id == "alien_commander":
        crown(p, 48, 18, 42, accent, WHITE)
        p.polygon(((48, 18), (72, 31), (78, 57), (64, 77), (48, 85),
                   (32, 77), (18, 57), (24, 31)), primary, OUTLINE, 4)
        p.ellipse((28, 39, 44, 56), secondary, OUTLINE, 2)
        p.ellipse((52, 39, 68, 56), secondary, OUTLINE, 2)
        p.arc((6, 23, 90, 88), 194, 346, accent, 3)
        p.ellipse((8, 49, 18, 59), accent, OUTLINE, 2)
        p.ellipse((78, 47, 88, 57), accent, OUTLINE, 2)
    else:
        raise ValueError("Unknown Enemy icon: " + icon_id)


def draw_boss(p, spec):
    primary, secondary, accent = spec.primary, spec.secondary, spec.accent
    icon_id = spec.icon_id
    shadow(p, (10, 77, 86, 89))
    if icon_id == "yeti_colossus":
        crown(p, 48, 18, 43, accent, WHITE)
        p.polygon(((20, 38), (7, 21), (31, 25), (39, 15), (48, 26),
                   (57, 15), (65, 25), (89, 21), (76, 39), (81, 70),
                   (62, 86), (34, 86), (15, 70)), primary, OUTLINE, 5)
        p.ellipse((26, 37, 70, 77), secondary, OUTLINE, 3)
        face(p, (39, 51), (57, 51), 65, happy=False)
        p.polygon(star_points(48, 36, 9, 4, 6), accent, OUTLINE, 2)
        p.line(((25, 70), (11, 82)), secondary, 5)
        p.line(((71, 70), (85, 82)), secondary, 5)
    elif icon_id == "orc_warlord":
        p.polygon(((18, 34), (31, 16), (65, 16), (78, 34), (73, 73),
                   (58, 87), (38, 87), (23, 73)), primary, OUTLINE, 5)
        p.polygon(((21, 34), (10, 19), (31, 27)), secondary, OUTLINE, 4)
        p.polygon(((75, 34), (86, 19), (65, 27)), secondary, OUTLINE, 4)
        crown(p, 48, 17, 45, accent, WHITE)
        p.ellipse((31, 44, 43, 56), INK)
        p.ellipse((53, 44, 65, 56), INK)
        p.polygon(((28, 62), (41, 69), (35, 80)), CREAM, OUTLINE, 2.5)
        p.polygon(((68, 62), (55, 69), (61, 80)), CREAM, OUTLINE, 2.5)
        p.line(((13, 75), (31, 32)), accent, 5)
        p.line(((83, 75), (65, 32)), accent, 5)
    elif icon_id == "azure_demon":
        p.polygon(((24, 37), (11, 12), (39, 28), (48, 17), (57, 28),
                   (85, 12), (72, 38), (78, 69), (61, 85), (35, 85),
                   (18, 69)), primary, OUTLINE, 5)
        p.ellipse((27, 34, 69, 76), secondary, OUTLINE, 3)
        p.polygon(((32, 47), (44, 43), (40, 56)), accent, OUTLINE, 2)
        p.polygon(((64, 47), (52, 43), (56, 56)), accent, OUTLINE, 2)
        p.ellipse((35, 47, 41, 53), INK)
        p.ellipse((55, 47, 61, 53), INK)
        p.polygon(star_points(48, 66, 10, 4, 6), accent, OUTLINE, 2)
        p.arc((8, 20, 88, 91), 195, 345, accent, 3)
    elif icon_id == "mushroom_monarch":
        p.rounded((36, 49, 61, 85), 9, secondary, OUTLINE, 5)
        p.ellipse((10, 21, 86, 63), primary, OUTLINE, 5)
        crown(p, 48, 18, 48, accent, WHITE)
        p.ellipse((25, 33, 39, 45), accent)
        p.ellipse((58, 31, 72, 43), secondary)
        face(p, (41, 63), (56, 63), 74, happy=False)
        for x, y in ((12, 70), (81, 66), (73, 84)):
            p.ellipse((x - 4, y - 4, x + 4, y + 4), accent, OUTLINE, 2)
    elif icon_id == "star_dragon":
        p.polygon(((48, 11), (60, 25), (78, 18), (73, 39), (87, 50),
                   (71, 58), (68, 78), (53, 71), (48, 88), (43, 71),
                   (28, 78), (25, 58), (9, 50), (23, 39), (18, 18),
                   (36, 25)), primary, OUTLINE, 5)
        p.polygon(((48, 26), (67, 37), (63, 66), (48, 79), (33, 66), (29, 37)),
                  secondary, OUTLINE, 3)
        p.polygon(star_points(48, 35, 10, 4), accent, OUTLINE, 2)
        p.ellipse((34, 49, 43, 58), INK)
        p.ellipse((53, 49, 62, 58), INK)
        p.polygon(((38, 66), (48, 72), (58, 66), (54, 79), (42, 79)),
                  accent, OUTLINE, 2)
        glint(p, 75, 27, 3)
    else:
        raise ValueError("Unknown Boss icon: " + icon_id)


DRAWERS = {
    "Characters": draw_character,
    "Weapons": draw_weapon,
    "Tomes": draw_tome,
    "PowerUps": draw_power_up,
    "Trinkets": draw_trinket,
    "Evolutions": draw_evolution,
    "Enemies": draw_enemy,
    "Bosses": draw_boss,
}


def project_root_from_script():
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    if project_root.name != "Project":
        raise RuntimeError("Generator must live under Project/Tools")
    required = (
        project_root / "Assets" / "UI" / "Icons" / "Survivor",
        project_root / "Scripts" / "SurvivorCatalogCharacters.py",
        project_root / "Scripts" / "SurvivorCatalogItems.py",
        project_root / "Scripts" / "SurvivorCatalogMeta.py",
        project_root / "Scripts" / "SurvivorCatalogWorld.py",
    )
    missing = [path.as_posix() for path in required if not path.exists()]
    if missing:
        raise RuntimeError("Missing generator prerequisite(s):\n  " + "\n  ".join(missing))
    return project_root


def catalog_icon_entries(project_root):
    scripts_path = str(project_root / "Scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    import SurvivorCatalogCharacters as characters
    import SurvivorCatalogItems as items
    import SurvivorCatalogMeta as meta
    import SurvivorCatalogWorld as world

    return {
        "Characters": list(characters.CHARACTERS),
        "Weapons": list(items.WEAPONS),
        "Tomes": list(items.TOMES),
        "PowerUps": list(meta.POWER_UPS),
        "Trinkets": list(items.TRINKETS),
        "Evolutions": list(items.EVOLUTIONS),
        "Enemies": list(world.ENEMIES),
        "Bosses": list(world.BOSSES),
    }


def validate_designs(project_root):
    by_category = {category: [] for category in CATEGORY_COUNTS}
    seen_ids = set()
    seen_glyphs = set()
    for design in DESIGNS:
        if design.category not in by_category:
            raise ValueError("Unknown icon category: " + design.category)
        key = (design.category, design.icon_id)
        if key in seen_ids:
            raise ValueError("Duplicate icon design: " + str(key))
        if design.glyph in seen_glyphs:
            raise ValueError("Design glyph labels must be unique: " + design.glyph)
        seen_ids.add(key)
        seen_glyphs.add(design.glyph)
        for value in (design.primary, design.secondary, design.accent, OUTLINE):
            ImageColor.getrgb(value)
        by_category[design.category].append(design.icon_id)

    catalog_entries = catalog_icon_entries(project_root)
    for category, expected_count in CATEGORY_COUNTS.items():
        actual_ids = by_category[category]
        catalog_ids = [entry["id"] for entry in catalog_entries[category]]
        if len(actual_ids) != expected_count:
            raise ValueError(
                "%s design count is %d, expected %d"
                % (category, len(actual_ids), expected_count)
            )
        if actual_ids != catalog_ids:
            raise ValueError(
                "%s icon IDs do not match the current Catalog:\n  designs=%s\n  catalog=%s"
                % (category, actual_ids, catalog_ids)
            )
        for design, entry in zip(
                [item for item in DESIGNS if item.category == category],
                catalog_entries[category]):
            expected_path = icon_asset_path(design)
            if entry.get("icon") != expected_path:
                raise ValueError(
                    "%s Catalog icon path mismatch: expected %s, got %s"
                    % (design.icon_id, expected_path, entry.get("icon"))
                )
    if len(DESIGNS) != sum(CATEGORY_COUNTS.values()):
        raise ValueError("Unexpected total icon count")


def render_png(design):
    working = Image.new("RGBA", (WORK_SIZE, WORK_SIZE), (0, 0, 0, 0))
    painter = Painter(working)
    DRAWERS[design.category](painter, design)
    icon = working.resize((ICON_SIZE, ICON_SIZE), RESAMPLE_LANCZOS)
    stream = io.BytesIO()
    icon.save(stream, format="PNG", optimize=False, compress_level=9)
    return stream.getvalue()


def inspect_png(payload, asset_path):
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        if image.mode != "RGBA":
            raise ValueError(asset_path + " is not RGBA")
        if image.size != (ICON_SIZE, ICON_SIZE):
            raise ValueError(asset_path + " is not 96x96")
        alpha = image.getchannel("A")
        alpha_values = list(alpha.getdata())
        if any(alpha.getpixel(point) != 0 for point in ((0, 0), (95, 0), (0, 95), (95, 95))):
            raise ValueError(asset_path + " does not have transparent corners")
        transparent_pixels = sum(value == 0 for value in alpha_values)
        if transparent_pixels < ICON_SIZE * ICON_SIZE * 0.20:
            raise ValueError(asset_path + " does not preserve a transparent background")
        alpha_bbox = alpha.getbbox()
        if alpha_bbox is None:
            raise ValueError(asset_path + " has no visible pixels")
        bbox_width = alpha_bbox[2] - alpha_bbox[0]
        bbox_height = alpha_bbox[3] - alpha_bbox[1]
        if bbox_width < 45 or bbox_height < 45 or bbox_width > 94 or bbox_height > 94:
            raise ValueError(asset_path + " has an unreadable or clipped silhouette")
        opaque_pixels = sum(value >= 160 for value in alpha_values)
        if opaque_pixels < 650:
            raise ValueError(asset_path + " has too little solid icon area")

        preview_hashes = {}
        for preview_size in (48, 64, 96):
            preview = image if preview_size == 96 else image.resize(
                (preview_size, preview_size), RESAMPLE_LANCZOS
            )
            preview_alpha = preview.getchannel("A")
            preview_bbox = preview_alpha.getbbox()
            if preview_bbox is None:
                raise ValueError(asset_path + " vanishes at %dpx" % preview_size)
            preview_width = preview_bbox[2] - preview_bbox[0]
            preview_height = preview_bbox[3] - preview_bbox[1]
            if preview_width < preview_size * 0.44 or preview_height < preview_size * 0.44:
                raise ValueError(asset_path + " is not legible at %dpx" % preview_size)
            visible = sum(value >= 96 for value in preview_alpha.getdata())
            if visible < preview_size * preview_size * 0.08:
                raise ValueError(asset_path + " has insufficient coverage at %dpx" % preview_size)
            preview_hashes[str(preview_size)] = hashlib.sha256(preview.tobytes()).hexdigest()

    return {
        "alpha_bbox": list(alpha_bbox),
        "opaque_pixels": opaque_pixels,
        "transparent_pixels": transparent_pixels,
        "preview_sha256": preview_hashes,
    }


def json_payload(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def build_payloads(project_root):
    icon_payloads = {}
    manifest_entries = []
    icon_hashes = set()
    preview_hashes = {"48": set(), "64": set(), "96": set()}

    for design in DESIGNS:
        asset_path = icon_asset_path(design)
        payload = render_png(design)
        details = inspect_png(payload, asset_path)
        digest = hashlib.sha256(payload).hexdigest()
        if digest in icon_hashes:
            raise ValueError("Generated PNG bytes are duplicated: " + asset_path)
        icon_hashes.add(digest)
        for preview_size, preview_digest in details["preview_sha256"].items():
            if preview_digest in preview_hashes[preview_size]:
                raise ValueError(
                    "Generated icons collapse to duplicate pixels at %spx: %s"
                    % (preview_size, asset_path)
                )
            preview_hashes[preview_size].add(preview_digest)

        icon_payloads[project_root / asset_path] = payload
        manifest_entries.append({
            "id": design.icon_id,
            "category": design.category,
            "path": asset_path,
            "sha256": digest,
            "size": len(payload),
            "dimensions": [ICON_SIZE, ICON_SIZE],
            "mode": "RGBA",
            "glyph": design.glyph,
            "colors": {
                "primary": design.primary,
                "secondary": design.secondary,
                "accent": design.accent,
                "outline": OUTLINE,
            },
            "variant": design.variant,
            "alpha_bbox": details["alpha_bbox"],
            "opaque_pixels": details["opaque_pixels"],
            "transparent_pixels": details["transparent_pixels"],
        })

    aggregate = hashlib.sha256()
    for output_path, payload in sorted(
            icon_payloads.items(), key=lambda item: item[0].as_posix()):
        relative_path = output_path.relative_to(project_root).as_posix()
        aggregate.update(relative_path.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(payload)

    manifest = {
        "schema_version": 1,
        "generator_version": GENERATOR_VERSION,
        "art_direction": "Starbloom candy colors, deep-purple outline, transparent background, code-native Pillow primitives; no external or generated-image inputs",
        "icon_size": [ICON_SIZE, ICON_SIZE],
        "generated_file_count": len(icon_payloads),
        "category_counts": CATEGORY_COUNTS,
        "aggregate_sha256": aggregate.hexdigest(),
        "files": manifest_entries,
    }
    manifest_payload = json_payload(manifest)
    return icon_payloads, manifest_payload, manifest


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    os.replace(str(temporary), str(path))


def check_generated(project_root, icon_payloads, manifest_payload):
    mismatches = []
    for output_path, expected_payload in sorted(
            icon_payloads.items(), key=lambda item: item[0].as_posix()):
        relative_path = output_path.relative_to(project_root).as_posix()
        if not output_path.is_file():
            mismatches.append("missing: " + relative_path)
        elif output_path.read_bytes() != expected_payload:
            mismatches.append("different: " + relative_path)
        else:
            inspect_png(output_path.read_bytes(), relative_path)

    manifest_path = project_root / MANIFEST_ASSET_PATH
    if not manifest_path.is_file():
        mismatches.append("missing: " + MANIFEST_ASSET_PATH)
    elif manifest_path.read_bytes() != manifest_payload:
        mismatches.append("different: " + MANIFEST_ASSET_PATH)
    if mismatches:
        raise RuntimeError(
            "Generated icon verification failed:\n  " + "\n  ".join(mismatches)
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="rebuild all payloads in memory and verify exact generated files",
    )
    arguments = parser.parse_args()

    project_root = project_root_from_script()
    validate_designs(project_root)
    icon_payloads, manifest_payload, manifest = build_payloads(project_root)

    if arguments.check:
        check_generated(project_root, icon_payloads, manifest_payload)
        mode = "check"
    else:
        for output_path, payload in sorted(
                icon_payloads.items(), key=lambda item: item[0].as_posix()):
            atomic_write(output_path, payload)
        atomic_write(project_root / MANIFEST_ASSET_PATH, manifest_payload)
        mode = "generate"

    print(json.dumps({
        "mode": mode,
        "result": "PASS",
        "generated_file_count": manifest["generated_file_count"],
        "category_counts": manifest["category_counts"],
        "aggregate_sha256": manifest["aggregate_sha256"],
        "manifest": MANIFEST_ASSET_PATH,
    }, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
