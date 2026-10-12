"""Pure deterministic rules for Starbloom Survivor region objectives.

This module deliberately has no ``HEngine`` dependency.  It owns the numeric
configuration for the four regions, their Domain Powers, encounter pressure,
and the final objective Boss flow so runtime code and headless contracts consume
the same rules.

The public configuration objects are recursively read-only.  Functions which
return events or snapshots return ordinary detached dictionaries so a caller
can safely add presentation/runtime metadata without mutating the rules.
"""

import math
from types import MappingProxyType


REGION_DORMANT = "DORMANT"
REGION_ARMING = "ARMING"
REGION_ASSAULT = "ASSAULT"
REGION_OUTSIDE_GRACE = "OUTSIDE_GRACE"
REGION_COOLDOWN = "COOLDOWN"
REGION_ACTIVATED = "ACTIVATED"

REGION_STATES = (
    REGION_DORMANT,
    REGION_ARMING,
    REGION_ASSAULT,
    REGION_OUTSIDE_GRACE,
    REGION_COOLDOWN,
    REGION_ACTIVATED,
)

OBJECTIVE_EXPLORATION = "EXPLORATION"
OBJECTIVE_REGION_ASSAULT = "REGION_ASSAULT"
OBJECTIVE_BOSS_READY = "BOSS_READY"
OBJECTIVE_BOSS_INTRO = "BOSS_INTRO"
OBJECTIVE_BOSS_ACTIVE = "BOSS_ACTIVE"
OBJECTIVE_VICTORY = "VICTORY"

OBJECTIVE_STATES = (
    OBJECTIVE_EXPLORATION,
    OBJECTIVE_REGION_ASSAULT,
    OBJECTIVE_BOSS_READY,
    OBJECTIVE_BOSS_INTRO,
    OBJECTIVE_BOSS_ACTIVE,
    OBJECTIVE_VICTORY,
)

REGION_IDS = ("star", "thunder", "water", "wind")


def _freeze_config(value):
    if isinstance(value, dict):
        return MappingProxyType({
            key: _freeze_config(item) for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_config(item) for item in value)
    if isinstance(value, set):
        return frozenset(_freeze_config(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, MappingProxyType):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, frozenset):
        return sorted(_plain(item) for item in value)
    return value


# Region identity decides roster and reward.  ``activationOrder`` (1..4), not
# identity, decides pressure, fixed Elites, reward budget, and chest tier.
REGION_CONFIG = _freeze_config({
    "star": {
        "id": "star",
        "anchorTag": "EventAnchor_NorthRift",
        "markerTag": "EventAnchor_NorthRift Ground Marker",
        "spawnTagPrefix": "EventSpawn_Star_",
        "clearRadius": 9.0,
        "enterRadius": 8.50,
        "holdRadius": 8.75,
        "authoredPosition": (-2.0, 5.84, 67.0),
        "direction": "north",
        "domainId": "domain_star",
        "fodder": ("green_blob", "pink_blob"),
        "specialists": ("bee_ranger", "ghost_ambusher", "alien_commander"),
    },
    "thunder": {
        "id": "thunder",
        "anchorTag": "EventAnchor_WestShrine",
        "markerTag": "EventAnchor_WestShrine Ground Marker",
        "spawnTagPrefix": "EventSpawn_Thunder_",
        "clearRadius": 7.5,
        "enterRadius": 7.0,
        "holdRadius": 7.25,
        "authoredPosition": (-61.0, 4.04, 6.0),
        "direction": "west",
        "domainId": "domain_thunder",
        "fodder": ("green_blob", "spiky_blob"),
        "specialists": ("orc_bruiser", "alien_charger", "crab_guard"),
    },
    "water": {
        "id": "water",
        "anchorTag": "EventAnchor_SouthWetland",
        "markerTag": "EventAnchor_SouthWetland Ground Marker",
        "spawnTagPrefix": "EventSpawn_Water_",
        "clearRadius": 9.0,
        "enterRadius": 8.50,
        "holdRadius": 8.75,
        "authoredPosition": (0.0, -0.96, -60.0),
        "direction": "south",
        "domainId": "domain_water",
        "fodder": ("green_blob", "pink_blob"),
        "specialists": ("mushroom_lobber", "yeti_zoner", "crab_guard"),
    },
    "wind": {
        "id": "wind",
        "anchorTag": "EventAnchor_EastBasin",
        "markerTag": "EventAnchor_EastBasin Ground Marker",
        "spawnTagPrefix": "EventSpawn_Wind_",
        "clearRadius": 11.0,
        "enterRadius": 10.50,
        "holdRadius": 10.75,
        "authoredPosition": (57.0, 1.44, 3.0),
        "direction": "east",
        "domainId": "domain_wind",
        "fodder": ("green_blob", "pink_blob"),
        "specialists": (
            "alien_charger", "bee_ranger", "bomb_spore", "ghost_ambusher",
        ),
    },
})

# Backward-friendly plural alias for callers which naturally use that name.
REGION_CONFIGS = REGION_CONFIG

DOMAIN_POWER_CONFIG = _freeze_config({
    "domain_star": {
        "id": "domain_star",
        "regionId": "star",
        "cooldown": 14.0,
        "warningSeconds": 0.70,
        "radius": 3.4,
        "baseDamage": 26.0,
        "damagePerPlayerLevel": 1.80,
        "vulnerability": 0.08,
        "vulnerabilitySeconds": 3.0,
        "bossHardControl": False,
        "targeting": "strongest_dense_target",
        "overcharge": {
            "ordinaryHealthFractionDamage": 0.72,
            "eliteHealthFractionDamage": 0.36,
            "bossHealthFractionDamage": 0.0,
            "radiusMultiplier": 2.0,
        },
        "assetKeys": {
            "castVfx": "domain/star/cast-vfx",
            "impactVfx": "domain/star/impact-vfx",
            "overchargeVfx": "domain/star/overcharge-vfx",
            "icon": "domain/star/icon",
        },
    },
    "domain_thunder": {
        "id": "domain_thunder",
        "regionId": "thunder",
        "cooldown": 11.0,
        "chainTargetsMin": 4,
        "chainTargetsMax": 6,
        "linkRange": 4.8,
        "baseDamage": 18.0,
        "damagePerPlayerLevel": 1.25,
        "interruptSeconds": 0.35,
        "bossHardControl": False,
        "bossActionDelaySeconds": 0.18,
        "targeting": "deterministic_chain",
        "overcharge": {
            "ordinaryHealthFractionDamage": 0.68,
            "eliteHealthFractionDamage": 0.34,
            "bossHealthFractionDamage": 0.0,
            "maximumTargets": 64,
        },
        "assetKeys": {
            "castVfx": "domain/thunder/cast-vfx",
            "impactVfx": "domain/thunder/impact-vfx",
            "overchargeVfx": "domain/thunder/overcharge-vfx",
            "icon": "domain/thunder/icon",
        },
    },
    "domain_water": {
        "id": "domain_water",
        "regionId": "water",
        "cooldown": 15.0,
        "radius": 4.2,
        "baseDamage": 20.0,
        "damagePerPlayerLevel": 1.35,
        "slowStrength": 0.25,
        "slowSeconds": 2.5,
        "pushStrength": 0.70,
        "bossDisplacement": False,
        "targeting": "densest_target",
        "synergy": {
            "weaponTag": "water",
            "areaMultiplier": 1.20,
            "telemetryOwner": "domain_water",
        },
        "overcharge": {
            "ordinaryHealthFractionDamage": 0.65,
            "eliteHealthFractionDamage": 0.32,
            "bossHealthFractionDamage": 0.0,
            "radiusMultiplier": 1.8,
        },
        "assetKeys": {
            "castVfx": "domain/water/cast-vfx",
            "impactVfx": "domain/water/impact-vfx",
            "overchargeVfx": "domain/water/overcharge-vfx",
            "icon": "domain/water/icon",
        },
    },
    "domain_wind": {
        "id": "domain_wind",
        "regionId": "wind",
        "cooldown": 17.0,
        "duration": 3.0,
        "tickInterval": 0.50,
        "radius": 4.4,
        "baseTickDamage": 8.0,
        "tickDamagePerPlayerLevel": 0.55,
        "pullStrength": 1.15,
        "bossDisplacement": False,
        "bossSlowStrength": 0.18,
        "targeting": "densest_target",
        "overcharge": {
            "ordinaryHealthFractionDamage": 0.70,
            "eliteHealthFractionDamage": 0.35,
            "bossHealthFractionDamage": 0.0,
            "radiusMultiplier": 1.9,
        },
        "assetKeys": {
            "castVfx": "domain/wind/cast-vfx",
            "impactVfx": "domain/wind/impact-vfx",
            "overchargeVfx": "domain/wind/overcharge-vfx",
            "icon": "domain/wind/icon",
        },
    },
})

# DOMAIN_IDS are the structured combat/telemetry ids and are also the stable
# DOMAIN_POWER_CONFIG keys.  Region-to-domain mapping remains in REGION_CONFIG.
DOMAIN_IDS = tuple(DOMAIN_POWER_CONFIG.keys())
DOMAIN_POWER_IDS = DOMAIN_IDS
DOMAIN_POWER_BY_REGION = _freeze_config({
    region_id: DOMAIN_POWER_CONFIG[REGION_CONFIG[region_id]["domainId"]]
    for region_id in REGION_IDS
})

DOMAIN_GLOBAL_VFX_SPACING = 1.10
DOMAIN_PROC_POLICY = _freeze_config({
    "countsAsWeapon": False,
    "entersWeaponSlots": False,
    "entersUpgradePool": False,
    "countsForWeaponQuests": False,
    "allowsTrinketProcs": False,
    "allowsRecursiveProcs": False,
})

OBJECTIVE_CONFIG = _freeze_config({
    "regionIds": REGION_IDS,
    "armingSeconds": 1.5,
    "assaultSeconds": 60.0,
    "outsideGraceSeconds": 1.25,
    "cooldownSeconds": 12.0,
    "localAliveRadius": 24.0,
    "cleanupDistance": 30.0,
    "centralTag": "Central Starbloom Plinth",
    "centralPosition": (0.0, 0.04, 0.0),
    "centralRadius": 4.5,
    "centralHoldSeconds": 2.0,
    "bossIntroSeconds": 3.0,
    "bossReadySpawnPauseSeconds": 9.0,
    "objectiveBossArchetypeId": "star_dragon",
    "objectiveBossEventId": "starbloom_final_objective",
    "domainGlobalVfxSpacing": DOMAIN_GLOBAL_VFX_SPACING,
    "maxMonsters": 320,
})

ENCOUNTER_TIERS = _freeze_config((
    {
        "order": 1,
        "localAliveStart": 50,
        "localAliveEnd": 85,
        "spawnFloor": 5.0,
        "spawnCap": 8.0,
        "fixedElites": 2,
        "healthMultiplier": 1.00,
        "damageMultiplier": 1.00,
        "xpBudget": 320.0,
        "goldBudget": 8,
        "burstCap": 14,
    },
    {
        "order": 2,
        "localAliveStart": 75,
        "localAliveEnd": 120,
        "spawnFloor": 8.0,
        "spawnCap": 12.0,
        "fixedElites": 3,
        "healthMultiplier": 1.18,
        "damageMultiplier": 1.10,
        "xpBudget": 650.0,
        "goldBudget": 12,
        "burstCap": 20,
    },
    {
        "order": 3,
        "localAliveStart": 105,
        "localAliveEnd": 160,
        "spawnFloor": 11.0,
        "spawnCap": 16.0,
        "fixedElites": 4,
        "healthMultiplier": 1.42,
        "damageMultiplier": 1.22,
        "xpBudget": 950.0,
        "goldBudget": 16,
        "burstCap": 28,
    },
    {
        "order": 4,
        "localAliveStart": 140,
        "localAliveEnd": 210,
        "spawnFloor": 15.0,
        "spawnCap": 22.0,
        "fixedElites": 5,
        "healthMultiplier": 1.72,
        "damageMultiplier": 1.38,
        "xpBudget": 1300.0,
        "goldBudget": 22,
        "burstCap": 36,
    },
))

GLOBAL_THREAT_BANDS = (
    (30, 45),
    (45, 60),
    (60, 80),
    (80, 105),
    (100, 125),
)

DIFFICULTY_COUNT_MULTIPLIERS = _freeze_config({
    "adventure": 1.0,
    "fierce": 1.15,
    "nightmare": 1.30,
})

CHEST_TIERS_BY_ACTIVATION_ORDER = (1, 2, 2, 3)
FIXED_ELITE_TIMES = (18.0, 34.0, 50.0)
FODDER_SHARE = 0.62
REGION_REWARD_XP_SCALE = 0.50

SPAWN_FAILURE_REASONS = (
    "invalid_socket",
    "ground_probe_failed",
    "inside_clear_radius",
    "too_close_to_player",
    "blocked_geometry",
    "underwater",
    "global_cap",
    "instantiate_failed",
    "unknown_archetype",
)

SPECIAL_WAVE_EVENTS = _freeze_config({
    "lane_rush": {
        "phase": "build_surround",
        "directionFractions": (0.0, 0.5),
        "spawnStyle": "lanes",
    },
    "four_side": {
        "phase": "ranged_pressure",
        "directionFractions": (0.0, 0.25, 0.5, 0.75),
        "spawnStyle": "sides",
    },
    "four_wall": {
        "phase": "surge",
        "directionFractions": (0.0, 0.25, 0.5, 0.75),
        "spawnStyle": "walls",
    },
    "charge_lanes": {
        "phase": "surge",
        "directionFractions": (0.125, 0.625),
        "spawnStyle": "charge_lanes",
    },
    "final_peak": {
        "phase": "final_peak",
        "directionFractions": (0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875),
        "spawnStyle": "all_ingress",
    },
})


def objective_config_snapshot():
    """Return a detached serializable copy of all objective-owned tuning."""

    return {
        "objective": _plain(OBJECTIVE_CONFIG),
        "regions": _plain(REGION_CONFIG),
        "domains": _plain(DOMAIN_POWER_CONFIG),
        "domainProcPolicy": _plain(DOMAIN_PROC_POLICY),
        "encounterTiers": _plain(ENCOUNTER_TIERS),
        "globalThreatBands": _plain(GLOBAL_THREAT_BANDS),
        "difficultyCountMultipliers": _plain(DIFFICULTY_COUNT_MULTIPLIERS),
        "chestTiers": list(CHEST_TIERS_BY_ACTIVATION_ORDER),
        "fixedEliteTimes": list(FIXED_ELITE_TIMES),
        "fodderShare": FODDER_SHARE,
        "regionRewardXpScale": REGION_REWARD_XP_SCALE,
        "specialWaveEvents": _plain(SPECIAL_WAVE_EVENTS),
    }


def _finite_nonnegative(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be numeric")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(name + " must be finite and non-negative")
    return result


def _finite_coordinate(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(name + " must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(name + " must be finite")
    return result


def _distance_squared(left_x, left_z, right_x, right_z):
    delta_x = left_x - right_x
    delta_z = left_z - right_z
    return delta_x * delta_x + delta_z * delta_z


class _RegionRunState(object):
    __slots__ = (
        "region_id",
        "state",
        "arming_elapsed",
        "assault_elapsed",
        "grace_elapsed",
        "cooldown_remaining",
        "attempts",
        "outside_count",
        "failure_count",
        "max_assault_progress",
        "arming_started_at",
        "assault_started_at",
        "completed_at",
        "activation_order",
        "completion_issued",
    )

    def __init__(self, region_id):
        self.region_id = region_id
        self.state = REGION_DORMANT
        self.arming_elapsed = 0.0
        self.assault_elapsed = 0.0
        self.grace_elapsed = 0.0
        self.cooldown_remaining = 0.0
        self.attempts = 0
        self.outside_count = 0
        self.failure_count = 0
        self.max_assault_progress = 0.0
        self.arming_started_at = None
        self.assault_started_at = None
        self.completed_at = None
        self.activation_order = 0
        self.completion_issued = False

    def snapshot(self):
        return {
            "regionId": self.region_id,
            "state": self.state,
            "armingElapsed": self.arming_elapsed,
            "assaultElapsed": self.assault_elapsed,
            "assaultRemaining": max(
                0.0, OBJECTIVE_CONFIG["assaultSeconds"] - self.assault_elapsed,
            ),
            "graceElapsed": self.grace_elapsed,
            "graceRemaining": max(
                0.0, OBJECTIVE_CONFIG["outsideGraceSeconds"] - self.grace_elapsed,
            ),
            "cooldownRemaining": self.cooldown_remaining,
            "attempts": self.attempts,
            "outsideCount": self.outside_count,
            "failureCount": self.failure_count,
            "maxAssaultProgress": self.max_assault_progress,
            "armingStartedAt": self.arming_started_at,
            "assaultStartedAt": self.assault_started_at,
            "completedAt": self.completed_at,
            "activationOrder": self.activation_order,
            "completionIssued": self.completion_issued,
        }


class RegionObjectiveController(object):
    """Deterministic four-region and final-Boss state machine.

    ``update`` consumes unscaled gameplay delta only.  Callers should either not
    call it while gameplay is paused or pass ``gameplay_active=False``.  World
    clock multipliers (including Hurry) are intentionally absent.
    """

    def __init__(self, region_positions=None, central_position=None):
        self.region_states = {
            region_id: _RegionRunState(region_id) for region_id in REGION_IDS
        }
        self.region_positions = {}
        for region_id in REGION_IDS:
            authored = REGION_CONFIG[region_id]["authoredPosition"]
            self.region_positions[region_id] = (float(authored[0]), float(authored[2]))
        for region_id, position in dict(region_positions or {}).items():
            self.set_region_position(region_id, position[0], position[-1])
        if central_position is None:
            central_position = OBJECTIVE_CONFIG["centralPosition"]
        self.central_position = (
            float(central_position[0]), float(central_position[-1]),
        )
        self.objective_state = OBJECTIVE_EXPLORATION
        self.active_region_id = None
        self.completed_regions = []
        self.raw_elapsed = 0.0
        self.central_hold_elapsed = 0.0
        self.boss_intro_elapsed = 0.0
        self.boss_spawn_request_issued = False
        self.objective_boss_spawned = False
        self.objective_boss_killed = False
        self.objective_boss_event_id = OBJECTIVE_CONFIG["objectiveBossEventId"]
        self.objective_boss_entity_id = None
        self.objective_boss_activation_id = None
        self.objective_boss_archetype_id = None
        self._event_serial = 0

    def set_region_position(self, region_id, x, z):
        if region_id not in REGION_CONFIG:
            raise ValueError("unknown region id: " + str(region_id))
        self.region_positions[region_id] = (
            _finite_coordinate(x, "region x"),
            _finite_coordinate(z, "region z"),
        )

    def set_central_position(self, x, z):
        self.central_position = (
            _finite_coordinate(x, "central x"),
            _finite_coordinate(z, "central z"),
        )

    def _event(self, event_type, **values):
        self._event_serial += 1
        event = {"type": event_type, "serial": self._event_serial}
        event.update(values)
        return event

    def _inside(self, region_id, player_x, player_z, radius_key):
        center_x, center_z = self.region_positions[region_id]
        radius = REGION_CONFIG[region_id][radius_key]
        return _distance_squared(
            player_x, player_z, center_x, center_z,
        ) <= radius * radius

    def _inside_central(self, player_x, player_z):
        center_x, center_z = self.central_position
        radius = OBJECTIVE_CONFIG["centralRadius"]
        return _distance_squared(
            player_x, player_z, center_x, center_z,
        ) <= radius * radius

    def _set_exploration_if_possible(self):
        if self.objective_state in (
                OBJECTIVE_BOSS_READY,
                OBJECTIVE_BOSS_INTRO,
                OBJECTIVE_BOSS_ACTIVE,
                OBJECTIVE_VICTORY):
            return
        self.objective_state = (
            OBJECTIVE_REGION_ASSAULT
            if self.active_region_id is not None else
            OBJECTIVE_EXPLORATION
        )

    def _start_arming(self, region_id):
        state = self.region_states[region_id]
        state.state = REGION_ARMING
        state.arming_elapsed = 0.0
        state.arming_started_at = self.raw_elapsed
        self.active_region_id = region_id
        self.objective_state = OBJECTIVE_REGION_ASSAULT
        return self._event("region_arming_started", regionId=region_id)

    def _start_assault(self, region_id):
        state = self.region_states[region_id]
        state.state = REGION_ASSAULT
        state.arming_elapsed = OBJECTIVE_CONFIG["armingSeconds"]
        state.grace_elapsed = 0.0
        state.attempts += 1
        state.assault_started_at = self.raw_elapsed
        return self._event(
            "region_assault_started",
            regionId=region_id,
            attemptId=state.attempts,
            activationOrder=len(self.completed_regions) + 1,
        )

    def _fail_active_assault(self, reason):
        region_id = self.active_region_id
        if region_id is None:
            return ()
        state = self.region_states[region_id]
        if state.state not in (REGION_ASSAULT, REGION_OUTSIDE_GRACE):
            return ()
        state.max_assault_progress = max(
            state.max_assault_progress, state.assault_elapsed,
        )
        state.assault_elapsed = 0.0
        state.arming_elapsed = 0.0
        state.grace_elapsed = 0.0
        state.cooldown_remaining = OBJECTIVE_CONFIG["cooldownSeconds"]
        state.failure_count += 1
        state.state = REGION_COOLDOWN
        return (
            self._event(
                "stop_region_spawns", regionId=region_id,
                attemptId=state.attempts, reason=reason,
            ),
            self._event(
                "region_failed", regionId=region_id,
                attemptId=state.attempts, reason=reason,
            ),
            self._event(
                "region_cooldown_started", regionId=region_id,
                seconds=OBJECTIVE_CONFIG["cooldownSeconds"], reason=reason,
            ),
        )

    def _complete_region(self, region_id):
        state = self.region_states[region_id]
        if state.state == REGION_ACTIVATED or state.completion_issued:
            return ()
        if self.active_region_id not in (None, region_id):
            raise RuntimeError("only the active region can complete")

        activation_order = len(self.completed_regions) + 1
        completion_id = "region:{0}:complete".format(region_id)
        state.state = REGION_ACTIVATED
        state.assault_elapsed = OBJECTIVE_CONFIG["assaultSeconds"]
        state.max_assault_progress = max(
            state.max_assault_progress, state.assault_elapsed,
        )
        state.completed_at = self.raw_elapsed
        state.activation_order = activation_order
        state.completion_issued = True
        self.completed_regions.append(region_id)
        self.active_region_id = None

        base = {
            "regionId": region_id,
            "activationOrder": activation_order,
            "completionId": completion_id,
        }
        events = [
            self._event("region_activated", **base),
            self._event("stop_region_spawns", **base),
            self._event(
                "grant_domain_power",
                domainId=REGION_CONFIG[region_id]["domainId"],
                **base
            ),
            self._event(
                "domain_overcharge",
                domainId=REGION_CONFIG[region_id]["domainId"],
                **base
            ),
            self._event("vacuum_encounter_xp", **base),
            self._event(
                "spawn_region_chest",
                tier=CHEST_TIERS_BY_ACTIVATION_ORDER[activation_order - 1],
                sourceKind="region_completion",
                zoneId=region_id,
                **base
            ),
            self._event("region_state_updated", completedCount=activation_order, **base),
            self._event("retire_excess_region_monsters", **base),
        ]

        if len(self.completed_regions) == len(REGION_IDS):
            self.objective_state = OBJECTIVE_BOSS_READY
            self.central_hold_elapsed = 0.0
            events.append(self._event(
                "boss_ready",
                eventId=self.objective_boss_event_id,
                suppressGlobalSpawnsSeconds=OBJECTIVE_CONFIG[
                    "bossReadySpawnPauseSeconds"
                ],
            ))
        else:
            self.objective_state = OBJECTIVE_EXPLORATION
        return tuple(events)

    def complete_region(self, region_id):
        """Deterministic scenario/test hook using the normal idempotent receipt."""

        if region_id not in self.region_states:
            raise ValueError("unknown region id: " + str(region_id))
        if self.objective_state in (
                OBJECTIVE_BOSS_READY,
                OBJECTIVE_BOSS_INTRO,
                OBJECTIVE_BOSS_ACTIVE,
                OBJECTIVE_VICTORY):
            return ()
        if self.region_states[region_id].state == REGION_ACTIVATED:
            return ()
        self.active_region_id = region_id
        self.objective_state = OBJECTIVE_REGION_ASSAULT
        return self._complete_region(region_id)

    def update(self, raw_dt, x, z, gameplay_active=True):
        """Advance with unscaled gameplay seconds and return ordered events."""

        raw_dt = _finite_nonnegative(raw_dt, "raw_dt")
        x = _finite_coordinate(x, "player x")
        z = _finite_coordinate(z, "player z")
        if not gameplay_active or raw_dt <= 0.0:
            return ()
        self.raw_elapsed += raw_dt
        events = []

        if self.objective_state == OBJECTIVE_VICTORY:
            return ()
        if self.objective_state == OBJECTIVE_BOSS_READY:
            if self._inside_central(x, z):
                self.central_hold_elapsed += raw_dt
                if self.central_hold_elapsed >= OBJECTIVE_CONFIG["centralHoldSeconds"]:
                    self.central_hold_elapsed = OBJECTIVE_CONFIG["centralHoldSeconds"]
                    self.objective_state = OBJECTIVE_BOSS_INTRO
                    self.boss_intro_elapsed = 0.0
                    events.append(self._event(
                        "boss_intro_started", eventId=self.objective_boss_event_id,
                    ))
            else:
                self.central_hold_elapsed = 0.0
            return tuple(events)
        if self.objective_state == OBJECTIVE_BOSS_INTRO:
            self.boss_intro_elapsed += raw_dt
            if self.boss_intro_elapsed >= OBJECTIVE_CONFIG["bossIntroSeconds"]:
                self.boss_intro_elapsed = OBJECTIVE_CONFIG["bossIntroSeconds"]
                self.objective_state = OBJECTIVE_BOSS_ACTIVE
                if not self.boss_spawn_request_issued:
                    self.boss_spawn_request_issued = True
                    events.append(self._event(
                        "boss_spawn_requested",
                        eventId=self.objective_boss_event_id,
                        archetypeId=OBJECTIVE_CONFIG["objectiveBossArchetypeId"],
                        objectiveBoss=True,
                        finalBoss=True,
                    ))
            return tuple(events)
        if self.objective_state == OBJECTIVE_BOSS_ACTIVE:
            return ()

        if self.active_region_id is None:
            for region_id in REGION_IDS:
                state = self.region_states[region_id]
                if state.state != REGION_DORMANT:
                    continue
                if self._inside(region_id, x, z, "enterRadius"):
                    events.append(self._start_arming(region_id))
                    break
            if self.active_region_id is None:
                self._set_exploration_if_possible()
                return tuple(events)

        region_id = self.active_region_id
        state = self.region_states[region_id]
        if state.state == REGION_ARMING:
            if not self._inside(region_id, x, z, "holdRadius"):
                state.state = REGION_DORMANT
                state.arming_elapsed = 0.0
                state.arming_started_at = None
                self.active_region_id = None
                self._set_exploration_if_possible()
                events.append(self._event("region_arming_cancelled", regionId=region_id))
                return tuple(events)
            state.arming_elapsed += raw_dt
            if state.arming_elapsed >= OBJECTIVE_CONFIG["armingSeconds"]:
                events.append(self._start_assault(region_id))
            return tuple(events)

        if state.state == REGION_ASSAULT:
            if not self._inside(region_id, x, z, "holdRadius"):
                state.state = REGION_OUTSIDE_GRACE
                state.grace_elapsed = 0.0
                state.outside_count += 1
                events.append(self._event(
                    "region_outside_grace_started",
                    regionId=region_id,
                    attemptId=state.attempts,
                    progress=state.assault_elapsed,
                ))
                return tuple(events)
            state.assault_elapsed += raw_dt
            state.max_assault_progress = max(
                state.max_assault_progress, state.assault_elapsed,
            )
            if state.assault_elapsed >= OBJECTIVE_CONFIG["assaultSeconds"]:
                events.extend(self._complete_region(region_id))
            return tuple(events)

        if state.state == REGION_OUTSIDE_GRACE:
            if self._inside(region_id, x, z, "enterRadius"):
                state.state = REGION_ASSAULT
                state.grace_elapsed = 0.0
                events.append(self._event(
                    "region_assault_resumed",
                    regionId=region_id,
                    attemptId=state.attempts,
                    progress=state.assault_elapsed,
                ))
                return tuple(events)
            state.grace_elapsed += raw_dt
            if state.grace_elapsed > OBJECTIVE_CONFIG["outsideGraceSeconds"]:
                events.extend(self._fail_active_assault("outside_grace_expired"))
            return tuple(events)

        if state.state == REGION_COOLDOWN:
            state.cooldown_remaining = max(0.0, state.cooldown_remaining - raw_dt)
            if state.cooldown_remaining <= 0.0:
                state.state = REGION_DORMANT
                self.active_region_id = None
                self._set_exploration_if_possible()
                events.append(self._event(
                    "region_cooldown_finished", regionId=region_id,
                ))
            return tuple(events)

        return tuple(events)

    def on_revive(self):
        """Preserve activated regions and fail only the current incomplete try."""

        if self.active_region_id is None:
            return ()
        state = self.region_states[self.active_region_id]
        if state.state in (REGION_ASSAULT, REGION_OUTSIDE_GRACE):
            return self._fail_active_assault("revive")
        if state.state == REGION_ARMING:
            region_id = self.active_region_id
            state.state = REGION_DORMANT
            state.arming_elapsed = 0.0
            state.arming_started_at = None
            self.active_region_id = None
            self._set_exploration_if_possible()
            return (self._event("region_arming_cancelled", regionId=region_id, reason="revive"),)
        return ()

    def is_region_spawn_enabled(self):
        if self.active_region_id is None:
            return False
        return self.region_states[self.active_region_id].state == REGION_ASSAULT

    def mark_boss_spawned(
            self,
            event_id,
            entity_id=None,
            activation_id=None,
            archetype_id="star_dragon"):
        """Bind the one objective Boss identity to its explicit event id."""

        if (
                self.objective_state != OBJECTIVE_BOSS_ACTIVE
                or event_id != self.objective_boss_event_id
                or archetype_id != OBJECTIVE_CONFIG["objectiveBossArchetypeId"]):
            return False
        if self.objective_boss_spawned:
            return (
                event_id == self.objective_boss_event_id
                and entity_id == self.objective_boss_entity_id
                and activation_id == self.objective_boss_activation_id
                and archetype_id == self.objective_boss_archetype_id
            )
        self.objective_boss_spawned = True
        self.objective_boss_entity_id = entity_id
        self.objective_boss_activation_id = activation_id
        self.objective_boss_archetype_id = archetype_id
        return True

    def mark_boss_killed(
            self,
            event_id,
            objective_boss,
            entity_id=None,
            activation_id=None,
            archetype_id="star_dragon",
            final_boss=True):
        """Accept victory only for the previously registered objective Boss.

        ``final_boss`` is intentionally not sufficient: it is a compatibility
        field for runtime monster state, while the event id plus registered
        activation form the authority.
        """

        del final_boss
        if self.objective_state == OBJECTIVE_VICTORY:
            return False
        if (
                self.objective_state != OBJECTIVE_BOSS_ACTIVE
                or not bool(objective_boss)
                or not self.objective_boss_spawned
                or event_id != self.objective_boss_event_id
                or archetype_id != self.objective_boss_archetype_id):
            return False
        if (
                self.objective_boss_entity_id is not None
                and entity_id != self.objective_boss_entity_id):
            return False
        if (
                self.objective_boss_activation_id is not None
                and activation_id != self.objective_boss_activation_id):
            return False
        self.objective_boss_killed = True
        self.objective_state = OBJECTIVE_VICTORY
        return True

    def snapshot(self):
        return {
            "objectiveState": self.objective_state,
            "activeRegion": self.active_region_id,
            "completedRegions": list(self.completed_regions),
            "completedCount": len(self.completed_regions),
            "rawElapsed": self.raw_elapsed,
            "centralHoldElapsed": self.central_hold_elapsed,
            "bossIntroElapsed": self.boss_intro_elapsed,
            "bossEventId": self.objective_boss_event_id,
            "bossSpawnRequested": self.boss_spawn_request_issued,
            "bossSpawned": self.objective_boss_spawned,
            "bossKilled": self.objective_boss_killed,
            "regions": {
                region_id: self.region_states[region_id].snapshot()
                for region_id in REGION_IDS
            },
        }


class KillRateEWMA(object):
    """Five-second exponential moving average of observed kills per second."""

    def __init__(self, window_seconds=5.0):
        self.window_seconds = max(
            0.001, _finite_nonnegative(window_seconds, "window_seconds"),
        )
        self.value = 0.0
        self.total_kills = 0
        self.total_seconds = 0.0

    def reset(self):
        self.value = 0.0
        self.total_kills = 0
        self.total_seconds = 0.0

    def update(self, raw_dt, kills=0):
        raw_dt = _finite_nonnegative(raw_dt, "raw_dt")
        if isinstance(kills, bool) or not isinstance(kills, int) or kills < 0:
            raise ValueError("kills must be a non-negative integer")
        if raw_dt <= 0.0:
            if kills:
                raise ValueError("kills require a positive sample duration")
            return self.value
        instantaneous = float(kills) / raw_dt
        alpha = 1.0 - math.exp(-raw_dt / self.window_seconds)
        self.value += alpha * (instantaneous - self.value)
        self.value = max(0.0, self.value)
        self.total_kills += kills
        self.total_seconds += raw_dt
        return self.value


def _tier(activation_order):
    if isinstance(activation_order, bool) or not isinstance(activation_order, int):
        raise ValueError("activation_order must be an integer")
    if activation_order < 1 or activation_order > len(ENCOUNTER_TIERS):
        raise ValueError("activation_order must be in [1, 4]")
    return ENCOUNTER_TIERS[activation_order - 1]


def _challenge_count_multiplier(challenge_tuning):
    if challenge_tuning is None:
        return 1.0
    if isinstance(challenge_tuning, dict) or hasattr(challenge_tuning, "get"):
        value = challenge_tuning.get("enemyCount", 1.0)
    else:
        value = challenge_tuning
    return _finite_nonnegative(value, "challenge enemyCount")


def fixed_elite_schedule(activation_order):
    count = int(_tier(activation_order)["fixedElites"])
    # Weight the later peak without omitting all early pressure.
    distributions = {
        2: (1, 0, 1),
        3: (1, 1, 1),
        4: (1, 1, 2),
        5: (1, 2, 2),
    }
    counts = distributions[count]
    return tuple({"time": time_value, "count": count_value}
                 for time_value, count_value in zip(FIXED_ELITE_TIMES, counts)
                 if count_value > 0)


def region_roster_weights(region_id, assault_elapsed=0.0):
    if region_id not in REGION_CONFIG:
        raise ValueError("unknown region id: " + str(region_id))
    assault_elapsed = _finite_nonnegative(assault_elapsed, "assault_elapsed")
    definition = REGION_CONFIG[region_id]
    fodder = definition["fodder"]
    specialists = definition["specialists"]
    fodder_weight = FODDER_SHARE / max(1, len(fodder))
    specialist_weight = (1.0 - FODDER_SHARE) / max(1, len(specialists))
    rows = []
    for enemy_id in fodder:
        rows.append({"enemyId": enemy_id, "weight": fodder_weight, "fodder": True})
    # Specialist availability grows over the four pressure quarters without
    # changing the aggregate fodder share.
    available_count = min(
        len(specialists),
        max(1, 1 + int(min(59.999, assault_elapsed) // 15.0)),
    )
    active_specialists = specialists[:available_count]
    active_weight = (1.0 - FODDER_SHARE) / max(1, len(active_specialists))
    for enemy_id in active_specialists:
        rows.append({"enemyId": enemy_id, "weight": active_weight, "fodder": False})
    return tuple(rows)


def global_threat_target(completed_regions, band_progress=0.5):
    if isinstance(completed_regions, bool) or not isinstance(completed_regions, int):
        raise ValueError("completed_regions must be an integer")
    if completed_regions < 0 or completed_regions >= len(GLOBAL_THREAT_BANDS):
        raise ValueError("completed_regions must be in [0, 4]")
    progress = max(0.0, min(1.0, _finite_nonnegative(band_progress, "band_progress")))
    start, end = GLOBAL_THREAT_BANDS[completed_regions]
    return int(round(start + (end - start) * progress))


def resolve_wave_event(event_id, socket_count, serial=0):
    if event_id not in SPECIAL_WAVE_EVENTS:
        raise ValueError("unknown wave event: " + str(event_id))
    if isinstance(socket_count, bool) or not isinstance(socket_count, int) or socket_count <= 0:
        raise ValueError("socket_count must be a positive integer")
    if isinstance(serial, bool) or not isinstance(serial, int):
        raise ValueError("serial must be an integer")
    definition = SPECIAL_WAVE_EVENTS[event_id]
    rotation = serial % socket_count
    indices = []
    for fraction in definition["directionFractions"]:
        index = (int(round(float(fraction) * socket_count)) + rotation) % socket_count
        if index not in indices:
            indices.append(index)
    return {
        "eventId": event_id,
        "phase": definition["phase"],
        "spawnStyle": definition["spawnStyle"],
        "socketIndices": indices,
        "directionCount": len(indices),
    }


def classify_region_cleanup(
        monsters,
        player_x,
        player_z,
        region_id,
        encounter_id,
        cooldown_complete,
        max_retire=8,
        retire_distance=None):
    """Classify cleanup without deleting anything.

    During grace/cooldown every living monster is retained.  Once cleanup is
    allowed, retirement is bounded per call; nearby engaged survivors are
    converted to ordinary world monsters instead of disappearing.
    """

    if region_id not in REGION_CONFIG:
        raise ValueError("unknown region id: " + str(region_id))
    if isinstance(max_retire, bool) or not isinstance(max_retire, int) or max_retire < 0:
        raise ValueError("max_retire must be a non-negative integer")
    if not cooldown_complete:
        return {"retire": [], "convert": [], "retained": []}
    if retire_distance is None:
        retire_distance = OBJECTIVE_CONFIG["cleanupDistance"]
    retire_distance = _finite_nonnegative(retire_distance, "retire_distance")
    retire_distance_sq = retire_distance * retire_distance
    retire = []
    convert = []
    retained = []
    for monster in monsters:
        if (
                monster.get("dead", False)
                or monster.get("regionId") != region_id
                or monster.get("encounterId") != encounter_id):
            continue
        key = monster.get("key", monster.get("entityId"))
        x = float(monster.get("x", 0.0))
        z = float(monster.get("z", 0.0))
        distance_sq = _distance_squared(x, z, player_x, player_z)
        b_engaged = bool(monster.get("engaged", distance_sq < retire_distance_sq))
        b_safe_to_retire = (
            distance_sq >= retire_distance_sq
            or (not b_engaged and distance_sq >= 12.0 * 12.0)
        )
        if b_safe_to_retire and len(retire) < max_retire:
            retire.append(key)
        elif distance_sq < retire_distance_sq:
            convert.append(key)
        else:
            retained.append(key)
    return {"retire": retire, "convert": convert, "retained": retained}


class EncounterDirector(object):
    """Pure local-population, spawn-rate, schedule, and anti-farm director."""

    def __init__(self, max_monsters=320):
        if isinstance(max_monsters, bool) or not isinstance(max_monsters, int):
            raise ValueError("max_monsters must be an integer")
        self.max_monsters = max(1, min(320, max_monsters))
        self.kill_rate = KillRateEWMA(5.0)
        self.region_budgets = {}
        self.active_region_id = None
        self.active_encounter_id = None
        self.active_attempt_id = None
        self.activation_order = 0
        self.spawn_credit = 0.0
        self.burst_available = True
        self.burst_cooldown = 0.0
        self.spawn_failures = {reason: 0 for reason in SPAWN_FAILURE_REASONS}
        self._elite_ledger = set()
        self._wave_event_ledger = set()

    def begin_attempt(
            self,
            region_id,
            attempt_id,
            activation_order,
            encounter_id=None):
        if region_id not in REGION_CONFIG:
            raise ValueError("unknown region id: " + str(region_id))
        if isinstance(attempt_id, bool) or not isinstance(attempt_id, int) or attempt_id <= 0:
            raise ValueError("attempt_id must be a positive integer")
        tier = _tier(activation_order)
        budget = self.region_budgets.get(region_id)
        if budget is None:
            budget = {
                "budgetTier": activation_order,
                "xpBudget": float(tier["xpBudget"]),
                "xpConsumed": 0.0,
                "goldBudget": int(tier["goldBudget"]),
                "goldConsumed": 0,
            }
            self.region_budgets[region_id] = budget
        elif activation_order > int(budget["budgetTier"]):
            # A different region may have completed between attempts.  The
            # prospective activation tier legitimately rises, but consumed
            # rewards are never restored; only the shared ceiling is expanded.
            budget["budgetTier"] = activation_order
            budget["xpBudget"] = max(
                budget["xpBudget"], float(tier["xpBudget"]),
            )
            budget["goldBudget"] = max(
                budget["goldBudget"], int(tier["goldBudget"]),
            )
        self.active_region_id = region_id
        self.active_encounter_id = (
            str(encounter_id) if encounter_id is not None
            else "region:" + region_id
        )
        self.active_attempt_id = attempt_id
        self.activation_order = activation_order
        self.spawn_credit = 0.0
        self.burst_available = True
        self.burst_cooldown = 0.0
        self.kill_rate.reset()
        return self.snapshot()

    def end_attempt(self, success=False):
        result = self.snapshot()
        result["success"] = bool(success)
        self.active_region_id = None
        self.active_encounter_id = None
        self.active_attempt_id = None
        self.activation_order = 0
        self.spawn_credit = 0.0
        self.burst_available = True
        self.burst_cooldown = 0.0
        self.kill_rate.reset()
        return result

    def local_target(
            self,
            activation_order,
            assault_progress,
            difficulty="adventure",
            challenge_tuning=None):
        tier = _tier(activation_order)
        progress = max(
            0.0,
            min(1.0, _finite_nonnegative(assault_progress, "assault_progress")),
        )
        difficulty_multiplier = DIFFICULTY_COUNT_MULTIPLIERS.get(difficulty)
        if difficulty_multiplier is None:
            raise ValueError("unknown difficulty: " + str(difficulty))
        challenge_multiplier = _challenge_count_multiplier(challenge_tuning)
        base = tier["localAliveStart"] + (
            tier["localAliveEnd"] - tier["localAliveStart"]
        ) * progress
        return min(
            self.max_monsters,
            int(round(base * difficulty_multiplier * challenge_multiplier)),
        )

    def spawn_rate(
            self,
            activation_order,
            difficulty="adventure",
            challenge_tuning=None,
            recent_kills_per_second=None):
        tier = _tier(activation_order)
        difficulty_multiplier = DIFFICULTY_COUNT_MULTIPLIERS.get(difficulty)
        if difficulty_multiplier is None:
            raise ValueError("unknown difficulty: " + str(difficulty))
        challenge_multiplier = _challenge_count_multiplier(challenge_tuning)
        scale = difficulty_multiplier * challenge_multiplier
        floor_value = float(tier["spawnFloor"]) * scale
        cap_value = float(tier["spawnCap"]) * scale
        if recent_kills_per_second is None:
            recent_kills_per_second = self.kill_rate.value
        recent_kills_per_second = _finite_nonnegative(
            recent_kills_per_second, "recent_kills_per_second",
        )
        return max(
            floor_value,
            min(cap_value, 1.15 * recent_kills_per_second),
        )

    def record_kills(self, raw_dt, kills):
        return self.kill_rate.update(raw_dt, kills)

    @staticmethod
    def count_local_alive(monsters, center_x, center_z, encounter_id, radius=24.0):
        radius = _finite_nonnegative(radius, "radius")
        radius_sq = radius * radius
        count = 0
        for monster in monsters:
            if monster.get("dead", False):
                continue
            if monster.get("encounterId") != encounter_id:
                continue
            x = float(monster.get("x", 0.0))
            z = float(monster.get("z", 0.0))
            if _distance_squared(x, z, center_x, center_z) <= radius_sq:
                count += 1
        return count

    def plan_spawn(
            self,
            raw_dt,
            assault_elapsed,
            local_alive,
            total_alive,
            difficulty="adventure",
            challenge_tuning=None,
            spawning_enabled=True,
            socket_count=8):
        raw_dt = _finite_nonnegative(raw_dt, "raw_dt")
        if any(isinstance(value, bool) or not isinstance(value, int) or value < 0
               for value in (local_alive, total_alive)):
            raise ValueError("alive counts must be non-negative integers")
        if self.active_region_id is None or not spawning_enabled:
            return {
                "spawnCount": 0,
                "burstCount": 0,
                "localTarget": 0,
                "spawnRate": 0.0,
                "waveEvents": [],
                "fixedElites": [],
                "reason": "inactive",
            }
        assault_elapsed = _finite_nonnegative(assault_elapsed, "assault_elapsed")
        previous_elapsed = max(0.0, assault_elapsed - raw_dt)
        progress = min(1.0, assault_elapsed / OBJECTIVE_CONFIG["assaultSeconds"])
        target = self.local_target(
            self.activation_order, progress, difficulty, challenge_tuning,
        )
        rate = self.spawn_rate(
            self.activation_order, difficulty, challenge_tuning,
        )
        self.spawn_credit += rate * raw_dt
        regular_count = int(self.spawn_credit)
        self.spawn_credit -= regular_count
        missing = max(0, target - local_alive)
        regular_count = min(regular_count, missing)

        self.burst_cooldown = max(0.0, self.burst_cooldown - raw_dt)
        if self.burst_cooldown <= 0.0:
            self.burst_available = True
        burst_count = 0
        if (
                target > 0
                and local_alive < target * 0.75
                and self.burst_available
                and missing > regular_count):
            burst_count = min(
                int(_tier(self.activation_order)["burstCap"]),
                missing - regular_count,
            )
            self.burst_available = False
            self.burst_cooldown = 5.0

        capacity = max(0, self.max_monsters - total_alive)
        requested = regular_count + burst_count
        spawn_count = min(requested, missing, capacity)
        if spawn_count < requested and capacity <= 0:
            self.record_spawn_failure("global_cap")
        effective_burst = min(burst_count, max(0, spawn_count - regular_count))
        if spawn_count < regular_count:
            # Credit only genuinely deferred regular work, with a bounded carry.
            self.spawn_credit = min(rate, self.spawn_credit + regular_count - spawn_count)

        return {
            "spawnCount": spawn_count,
            "burstCount": effective_burst,
            "localTarget": target,
            "localAlive": local_alive,
            "missing": missing,
            "spawnRate": rate,
            "recentKillsPerSecond": self.kill_rate.value,
            "waveEvents": list(self.wave_events_due(
                previous_elapsed,
                assault_elapsed,
                self.active_region_id,
                socket_count,
            )),
            "fixedElites": list(self.fixed_elites_due(
                previous_elapsed, assault_elapsed, self.activation_order,
            )),
            "reason": "global_cap" if capacity <= 0 and missing > 0 else "ok",
        }

    @staticmethod
    def wave_event(event_id, socket_count, serial=0):
        return resolve_wave_event(event_id, socket_count, serial)

    def wave_events_due(
            self,
            previous_elapsed,
            current_elapsed,
            region_id,
            socket_count=8):
        if region_id not in REGION_CONFIG:
            raise ValueError("unknown region id: " + str(region_id))
        previous_elapsed = _finite_nonnegative(previous_elapsed, "previous_elapsed")
        current_elapsed = _finite_nonnegative(current_elapsed, "current_elapsed")
        if current_elapsed < previous_elapsed:
            raise ValueError("current_elapsed cannot precede previous_elapsed")
        middle_event = {
            "star": "four_side",
            "thunder": "charge_lanes",
            "water": "four_wall",
            "wind": "charge_lanes",
        }[region_id]
        schedule = ((15.0, "lane_rush"), (30.0, middle_event), (45.0, "final_peak"))
        result = []
        for threshold, event_id in schedule:
            ledger_key = (
                self.active_encounter_id,
                self.active_attempt_id,
                event_id,
                threshold,
            )
            if previous_elapsed < threshold <= current_elapsed and ledger_key not in self._wave_event_ledger:
                self._wave_event_ledger.add(ledger_key)
                event = resolve_wave_event(
                    event_id,
                    socket_count,
                    (self.active_attempt_id or 1) + int(threshold),
                )
                event["time"] = threshold
                event["regionId"] = region_id
                result.append(event)
        return tuple(result)

    def fixed_elites_due(
            self,
            previous_elapsed,
            current_elapsed,
            activation_order=None):
        if activation_order is None:
            activation_order = self.activation_order
        previous_elapsed = _finite_nonnegative(previous_elapsed, "previous_elapsed")
        current_elapsed = _finite_nonnegative(current_elapsed, "current_elapsed")
        if current_elapsed < previous_elapsed:
            raise ValueError("current_elapsed cannot precede previous_elapsed")
        due = []
        for row in fixed_elite_schedule(activation_order):
            ledger_key = (
                self.active_encounter_id,
                self.active_attempt_id,
                "elite",
                row["time"],
            )
            if (
                    previous_elapsed < row["time"] <= current_elapsed
                    and ledger_key not in self._elite_ledger):
                self._elite_ledger.add(ledger_key)
                due.append({
                    "time": row["time"],
                    "count": row["count"],
                    "attemptId": self.active_attempt_id,
                })
        return tuple(due)

    def consume_xp(self, region_id, requested):
        requested = _finite_nonnegative(requested, "requested xp")
        budget = self.region_budgets.get(region_id)
        if budget is None:
            return 0.0
        remaining = max(0.0, budget["xpBudget"] - budget["xpConsumed"])
        consumed = min(remaining, requested)
        budget["xpConsumed"] += consumed
        return consumed

    def consume_gold(self, region_id, requested):
        if isinstance(requested, bool) or not isinstance(requested, int) or requested < 0:
            raise ValueError("requested gold must be a non-negative integer")
        budget = self.region_budgets.get(region_id)
        if budget is None:
            return 0
        remaining = max(0, budget["goldBudget"] - budget["goldConsumed"])
        consumed = min(remaining, requested)
        budget["goldConsumed"] += consumed
        return consumed

    @staticmethod
    def scaled_region_xp(base_xp):
        return _finite_nonnegative(base_xp, "base_xp") * REGION_REWARD_XP_SCALE

    def record_spawn_failure(self, reason, count=1):
        if reason not in self.spawn_failures:
            raise ValueError("unknown spawn failure reason: " + str(reason))
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("failure count must be a non-negative integer")
        self.spawn_failures[reason] += count

    def snapshot(self):
        return {
            "activeRegion": self.active_region_id,
            "encounterId": self.active_encounter_id,
            "attemptId": self.active_attempt_id,
            "activationOrder": self.activation_order,
            "recentKillsPerSecond": self.kill_rate.value,
            "spawnCredit": self.spawn_credit,
            "burstCooldown": self.burst_cooldown,
            "spawnFailures": dict(self.spawn_failures),
            "budgets": {
                region_id: dict(values)
                for region_id, values in self.region_budgets.items()
            },
        }
