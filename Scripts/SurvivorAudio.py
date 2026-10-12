"""Semantic audio event bank for the Survivor game mode.

Gameplay code posts event names through ``SurvivorAudio`` and never needs to
know about asset paths, buses, spatial settings, or voice limits.
"""

import time

import HEngine
from SurvivorRuntimeAssets import asset_path


AUDIO_AVAILABLE = hasattr(HEngine, "Audio")


ASSET_PATHS = {
    "music_menu": asset_path("audio/music-menu"),
    "music_gameplay": asset_path("audio/music-gameplay"),
    "ui_click": asset_path("audio/ui-click"),
    "ui_confirm": asset_path("audio/ui-confirm"),
    "ui_error": asset_path("audio/ui-error"),
    "level_up": asset_path("audio/level-up"),
    "xp_pickup": asset_path("audio/xp-pickup"),
    "boss_alert": asset_path("audio/boss-alert"),
    "cast_light": asset_path("audio/cast-light"),
    "cast_energy": asset_path("audio/cast-energy"),
    "cast_heavy": asset_path("audio/cast-heavy"),
    "monster_hit_01": asset_path("audio/monster-hit-01"),
    "monster_hit_02": asset_path("audio/monster-hit-02"),
    "monster_hit_03": asset_path("audio/monster-hit-03"),
    "monster_death_01": asset_path("audio/monster-death-01"),
    "monster_death_02": asset_path("audio/monster-death-02"),
    "player_hit": asset_path("audio/player-hit"),
}


MUSIC = {
    "menu": {
        "path": ASSET_PATHS["music_menu"],
        "volume": 0.42,
    },
    "gameplay": {
        "path": ASSET_PATHS["music_gameplay"],
        "volume": 0.36,
    },
}


EVENTS = {
    "ui_click": {
        "paths": (ASSET_PATHS["ui_click"],),
        "bus": "UI",
        "volume": 0.62,
        "cooldown": 0.04,
        "max_instances": 4,
    },
    "ui_confirm": {
        "paths": (ASSET_PATHS["ui_confirm"],),
        "bus": "UI",
        "volume": 0.72,
        "cooldown": 0.08,
        "max_instances": 2,
    },
    "ui_error": {
        "paths": (ASSET_PATHS["ui_error"],),
        "bus": "UI",
        "volume": 0.68,
        "cooldown": 0.25,
        "max_instances": 1,
    },
    "level_up": {
        "paths": (ASSET_PATHS["level_up"],),
        "bus": "UI",
        "volume": 0.84,
        "cooldown": 0.35,
        "max_instances": 1,
    },
    "xp_pickup": {
        "paths": (ASSET_PATHS["xp_pickup"],),
        "bus": "Gameplay",
        "volume": 0.34,
        "pitch_variation": 0.05,
        "cooldown": 0.06,
        "max_instances": 3,
    },
    "boss_alert": {
        "paths": (ASSET_PATHS["boss_alert"],),
        "bus": "UI",
        "volume": 0.92,
        "cooldown": 0.5,
        "max_instances": 1,
    },
    "cast_light": {
        "paths": (ASSET_PATHS["cast_light"],),
        "bus": "Gameplay",
        "volume": 0.46,
        "pitch_variation": 0.06,
        "cooldown": 0.08,
        "max_instances": 4,
    },
    "cast_energy": {
        "paths": (ASSET_PATHS["cast_energy"],),
        "bus": "Gameplay",
        "volume": 0.50,
        "pitch_variation": 0.05,
        "cooldown": 0.10,
        "max_instances": 3,
    },
    "cast_heavy": {
        "paths": (ASSET_PATHS["cast_heavy"],),
        "bus": "Gameplay",
        "volume": 0.54,
        "pitch_variation": 0.04,
        "cooldown": 0.15,
        "max_instances": 3,
    },
    "monster_hit": {
        "paths": (
            ASSET_PATHS["monster_hit_01"],
            ASSET_PATHS["monster_hit_02"],
            ASSET_PATHS["monster_hit_03"],
        ),
        "bus": "Gameplay",
        "volume": 0.40,
        "pitch_variation": 0.08,
        "cooldown": 0.06,
        "max_instances": 10,
        "spatial": True,
    },
    "monster_death": {
        "paths": (
            ASSET_PATHS["monster_death_01"],
            ASSET_PATHS["monster_death_02"],
        ),
        "bus": "Gameplay",
        "volume": 0.54,
        "pitch_variation": 0.06,
        "cooldown": 0.10,
        "max_instances": 7,
        "spatial": True,
    },
    "player_hit": {
        "paths": (ASSET_PATHS["player_hit"],),
        "bus": "Gameplay",
        "volume": 0.72,
        "pitch_variation": 0.03,
        "cooldown": 0.18,
        "max_instances": 2,
    },
    "game_over": {
        "paths": (ASSET_PATHS["ui_error"],),
        "bus": "UI",
        "volume": 0.82,
        "pitch": 0.82,
        "cooldown": 0.5,
        "max_instances": 1,
    },
}

EVENTS.update({
    "purchase": dict(EVENTS["ui_confirm"], pitch=1.06, cooldown=0.12),
    "insufficient_gold": dict(EVENTS["ui_error"], pitch=0.90, cooldown=0.30),
    "quest_complete": dict(EVENTS["level_up"], pitch=1.08, cooldown=0.35),
    "new_unlock": dict(EVENTS["ui_confirm"], pitch=1.14, cooldown=0.30),
    "gold_settlement": dict(EVENTS["xp_pickup"], pitch=1.03, cooldown=0.20),
})


WEAPON_EVENT = {
    "thunder": "cast_energy",
    "ring": "cast_light",
    "fireball": "cast_heavy",
    "moonblade": "cast_light",
    "bubble": "cast_light",
    "tornado": "cast_energy",
    "starfall": "cast_heavy",
    "aura": "cast_energy",
    "dagger": "cast_light",
    "starwheel": "cast_energy",
    "petalstorm": "cast_light",
    "comet": "cast_energy",
    "honeyneedle": "cast_light",
    "sporecap": "cast_heavy",
    "phantombell": "cast_energy",
    "coralanchor": "cast_heavy",
    "prismorbit": "cast_energy",
    "acornmortar": "cast_heavy",
    "frostorb": "cast_light",
    "gravityyoyo": "cast_energy",
    "rainbowrail": "cast_heavy",
}


class SurvivorAudio:
    """Owns Survivor music and one-shot voices behind semantic events."""

    _PITCH_STEPS = (-1.0, 0.35, -0.25, 0.75, 0.0)

    def __init__(self):
        self._music_handle = 0
        self._music_name = None
        self._active = {}
        self._last_played = {}
        self._variant_cursor = {}

    def update(self, dt):
        del dt
        if not AUDIO_AVAILABLE:
            return
        for event in tuple(self._active):
            self._active[event] = [
                handle
                for handle in self._active[event]
                if (
                    HEngine.Audio.IsPlaying(handle)
                    or HEngine.Audio.IsPaused(handle)
                )
            ]
            if not self._active[event]:
                del self._active[event]

    def play_music(self, name):
        if not AUDIO_AVAILABLE:
            return 0
        music = MUSIC.get(name)
        if music is None:
            return 0

        if (
            self._music_name == name
            and self._music_handle
            and (
                HEngine.Audio.IsPlaying(self._music_handle)
                or HEngine.Audio.IsPaused(self._music_handle)
            )
        ):
            return self._music_handle

        if self._music_handle:
            HEngine.Audio.Stop(self._music_handle)

        self._music_handle = HEngine.Audio.Play(
            music["path"],
            HEngine.Audio.Bus.Music,
            music["volume"],
            1.0,
            True,
            True,
            0.0,
        )
        self._music_name = name if self._music_handle else None
        return self._music_handle

    def post(self, event, position=None):
        if not AUDIO_AVAILABLE:
            return 0
        spec = EVENTS.get(event)
        if spec is None:
            return 0

        now = time.monotonic()
        last_played = self._last_played.get(event, -1000.0)
        if now - last_played < spec.get("cooldown", 0.0):
            return 0

        active = [
            handle
            for handle in self._active.get(event, ())
            if HEngine.Audio.IsPlaying(handle) or HEngine.Audio.IsPaused(handle)
        ]
        if len(active) >= spec.get("max_instances", 1):
            self._active[event] = active
            return 0

        paths = spec["paths"]
        play_count = self._variant_cursor.get(event, 0)
        cursor = play_count % len(paths)
        self._variant_cursor[event] = play_count + 1

        pitch_variation = spec.get("pitch_variation", 0.0)
        pitch_step = self._PITCH_STEPS[play_count % len(self._PITCH_STEPS)]
        pitch = spec.get("pitch", 1.0) + pitch_variation * pitch_step
        bus = getattr(HEngine.Audio.Bus, spec["bus"])

        if spec.get("spatial", False) and position is not None:
            handle = HEngine.Audio.Play3D(
                paths[cursor],
                position,
                bus,
                spec.get("volume", 1.0),
                pitch,
                spec.get("min_distance", 2.0),
                spec.get("max_distance", 28.0),
                spec.get("rolloff", 1.25),
                False,
                False,
            )
        else:
            handle = HEngine.Audio.Play(
                paths[cursor],
                bus,
                spec.get("volume", 1.0),
                pitch,
                False,
                False,
                0.0,
            )

        if handle:
            active.append(handle)
            self._active[event] = active
            self._last_played[event] = now
        return handle

    def weapon_cast(self, code, position):
        event = WEAPON_EVENT.get(code)
        return self.post(event, position) if event else 0

    def reset_gameplay(self):
        if not AUDIO_AVAILABLE:
            return
        HEngine.Audio.StopBus(HEngine.Audio.Bus.Gameplay)
        for event in tuple(self._active):
            if EVENTS.get(event, {}).get("bus") == "Gameplay":
                del self._active[event]
                self._last_played.pop(event, None)

    @staticmethod
    def set_music_ducked(b_ducked):
        if not AUDIO_AVAILABLE:
            return
        HEngine.Audio.SetBusVolume(
            HEngine.Audio.Bus.Music,
            0.55 if b_ducked else 1.0,
        )

    def stop(self):
        self.set_music_ducked(False)
        handles = set()
        if self._music_handle:
            handles.add(self._music_handle)
        for active in self._active.values():
            handles.update(active)
        if AUDIO_AVAILABLE:
            for handle in handles:
                HEngine.Audio.Stop(handle)

        self._music_handle = 0
        self._music_name = None
        self._active.clear()
        self._last_played.clear()
        self._variant_cursor.clear()
