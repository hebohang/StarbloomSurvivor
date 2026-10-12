"""HEngine integration for Region objectives, encounters, and final Boss flow."""

import math
import os
import time

import HEngine
import SurvivorSession

from SurvivorRegionObjectives import (
    DOMAIN_POWER_CONFIG,
    ENCOUNTER_TIERS,
    OBJECTIVE_BOSS_ACTIVE,
    OBJECTIVE_BOSS_INTRO,
    OBJECTIVE_BOSS_READY,
    OBJECTIVE_CONFIG,
    REGION_ACTIVATED,
    REGION_ARMING,
    REGION_ASSAULT,
    REGION_CONFIG,
    REGION_COOLDOWN,
    REGION_DORMANT,
    REGION_IDS,
    REGION_OUTSIDE_GRACE,
    EncounterDirector,
    RegionObjectiveController,
    global_threat_target,
    region_roster_weights,
    resolve_wave_event,
)
from SurvivorRuntimeAssets import asset_path


_CURRENT_OBJECTIVE_DIAGNOSTIC = {}
_OBJECTIVE_TIMING_ENABLED = os.environ.get("HE_SURVIVOR_OBJECTIVE_TIMINGS") == "1"
_LOCAL_ALIVE_VERIFY = os.environ.get("HE_SURVIVOR_LOCAL_ALIVE_VERIFY") == "1"
_OBJECTIVE_TIMING_SAMPLES = 0
_OBJECTIVE_TIMING_TOTALS = {}
_OBJECTIVE_TIMING_PEAKS = {}


def _timed_objective_call(name, function, *args, **kwargs):
    if not _OBJECTIVE_TIMING_ENABLED:
        return function(*args, **kwargs)
    start_ns = time.perf_counter_ns()
    try:
        return function(*args, **kwargs)
    finally:
        elapsed_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
        _OBJECTIVE_TIMING_TOTALS[name] = _OBJECTIVE_TIMING_TOTALS.get(name, 0.0) + elapsed_ms
        _OBJECTIVE_TIMING_PEAKS[name] = max(
            _OBJECTIVE_TIMING_PEAKS.get(name, 0.0), elapsed_ms,
        )


def current_objective_diagnostic():
    """Return the latest bounded Agent/GM-readable objective snapshot."""

    return dict(_CURRENT_OBJECTIVE_DIAGNOSTIC)


class SurvivorObjectivesMixin:
    REGION_SOCKET_COUNT = 10
    REGION_SPAWN_BUDGET_PER_FRAME = 8
    REGION_CLEANUP_BUDGET_PER_FRAME = 5
    REGION_TELEMETRY_SAMPLE_INTERVAL = 0.50
    BOSS_LEASH_START_DISTANCE = 35.0
    BOSS_LEASH_RETURN_SPEED = 4.0
    BOSS_LEASH_HEAL_PER_SECOND = 0.0015

    def _find_tagged_transform(self, tag, required=True):
        entity = HEngine.FindEntityByTag(tag)
        if entity is not None and entity.HasComponent("Transform"):
            return entity, entity.GetComponent("Transform")
        if required:
            raise RuntimeError("Missing transform-only Survivor scene tag: " + tag)
        return None, None

    def _load_region_scene_contract(self):
        self.region_anchors = {}
        self.region_markers = {}
        self.region_barriers = {}
        self.region_spawn_sockets = {}
        positions = {}
        for region_id in REGION_IDS:
            config = REGION_CONFIG[region_id]
            anchor_entity, anchor_transform = self._find_tagged_transform(
                config["anchorTag"],
            )
            marker_entity, marker_transform = self._find_tagged_transform(
                config["markerTag"],
            )
            barrier_entity, barrier_transform = self._find_tagged_transform(
                config["anchorTag"] + " Barrier Dome",
            )
            anchor_position = anchor_transform.Translation
            authored = config["authoredPosition"]
            if (
                    abs(anchor_position.x - authored[0]) > 0.02
                    or abs(anchor_position.z - authored[2]) > 0.02):
                raise RuntimeError(config["anchorTag"] + " moved from its authored XZ")
            self.region_anchors[region_id] = (anchor_entity, anchor_transform)
            self.region_markers[region_id] = (marker_entity, marker_transform)
            self.region_barriers[region_id] = (
                barrier_entity,
                barrier_transform,
            )
            barrier_transform.Scale = HEngine.vec3(0.001, 0.001, 0.001)
            positions[region_id] = (anchor_position.x, anchor_position.z)

            sockets = []
            prefix = config["spawnTagPrefix"]
            for index in range(self.REGION_SOCKET_COUNT):
                tag = prefix + ("%02d" % index)
                entity, transform = self._find_tagged_transform(tag)
                position = transform.Translation
                dx = position.x - anchor_position.x
                dz = position.z - anchor_position.z
                distance_sq = dx * dx + dz * dz
                if distance_sq <= config["clearRadius"] ** 2:
                    raise RuntimeError(tag + " is inside its Region clear radius")
                if position.x * position.x + position.z * position.z < 18.0 * 18.0:
                    raise RuntimeError(tag + " is too close to the player start")
                sockets.append({
                    "tag": tag,
                    "entity": entity,
                    "transform": transform,
                    "x": position.x,
                    "y": position.y,
                    "z": position.z,
                    "direction": math.atan2(dz, dx),
                })
            if len(sockets) != self.REGION_SOCKET_COUNT:
                raise RuntimeError(region_id + " has an incomplete spawn socket set")
            self.region_spawn_sockets[region_id] = tuple(sockets)

        central_entity, central_transform = self._find_tagged_transform(
            OBJECTIVE_CONFIG["centralTag"],
        )
        self.objective_central_entity = central_entity
        self.objective_central_transform = central_transform
        central = central_transform.Translation
        return positions, (central.x, central.z)

    def _reset_region_objectives(self):
        positions, central = self._load_region_scene_contract()
        self.objective_controller = RegionObjectiveController(positions, central)
        self.encounter_director = EncounterDirector(self.MAX_MONSTERS)
        self.objective_reward_receipts = set()
        self.pending_objective_retry_events = []
        self.objective_newly_discovered_domains = set()
        self.region_cleanup_queue = []
        self.region_historical_tail_cleanup = None
        self.region_completion_order = []
        self.region_spawn_serial = 0
        self.region_kills_since_sample = 0
        self.region_last_plan = {
            "localAlive": 0,
            "localTarget": 0,
            "spawnRate": 0.0,
            "recentKillsPerSecond": 0.0,
        }
        self.region_health_at_attempt_start = {}
        self.region_health_lost = {region_id: 0.0 for region_id in REGION_IDS}
        self.region_fixed_elites_spawned = {region_id: 0 for region_id in REGION_IDS}
        self.region_fixed_elites_pending = {region_id: 0 for region_id in REGION_IDS}
        self.region_burst_spawns_pending = {region_id: 0 for region_id in REGION_IDS}
        self.region_random_elites_spawned = {region_id: 0 for region_id in REGION_IDS}
        self.region_local_alive_samples = {region_id: [] for region_id in REGION_IDS}
        self.region_sample_timer = 0.0
        self.global_spawn_suppression_remaining = 0.0
        self.global_threat_tier_elapsed = 0.0
        self.objective_beacon_timer = 0.0
        self.region_visual_time = 0.0
        self.objective_boss = None
        self.objective_boss_spawn_raw_time = None
        self.objective_boss_ttk = 0.0
        self.objective_boss_phase = 0
        self.objective_boss_phase_started = 0.0
        self.objective_boss_phase_durations = {1: 0.0, 2: 0.0, 3: 0.0}
        self.objective_boss_enraged = False
        self.pending_objective_boss_event = None
        self.pending_boss_domain_responses = []
        self.capture_region_prefill_request = None
        self._apply_objective_capture_scenario()
        self._publish_objective_diagnostic()

    def _active_region_snapshot(self):
        snapshot = self.objective_controller.snapshot()
        region_id = snapshot["activeRegion"]
        return (
            region_id,
            snapshot["regions"].get(region_id) if region_id is not None else None,
        )

    def _banner(self, key, seconds=2.2):
        self.banner_key = key
        self.banner_timer = max(self.banner_timer, float(seconds))
        if self.document_id:
            self._set_hud_text("banner", self._text(key))

    def _queue_objective_retry_event(self, event):
        key = (event.get("type", ""), event.get("completionId", ""))
        if any(
                (queued.get("type", ""), queued.get("completionId", "")) == key
                for queued in self.pending_objective_retry_events):
            return
        self.pending_objective_retry_events.append(dict(event))

    @staticmethod
    def _runtime_domain_key(domain_power_id):
        return str(domain_power_id)

    def _discover_domain(self, domain_power_id):
        discovered = self.profile.setdefault("discoveredDomains", [])
        if domain_power_id in discovered:
            return False
        staged = __import__("SurvivorProfile").validate_profile(self.profile)
        staged.setdefault("discoveredDomains", []).append(domain_power_id)
        if not self._save_progression(staged):
            return False
        return True

    def _process_objective_events(self, events, player_pos):
        for event in events:
            event_type = event["type"]
            region_id = event.get("regionId", "")
            if event_type == "region_arming_started":
                self._banner("region_arming_banner", 1.5)
            elif event_type == "region_assault_started":
                self._begin_region_attempt(event, player_pos)
                self._banner("region_assault_banner", 2.0)
            elif event_type == "region_outside_grace_started":
                self._banner("region_grace_banner", 1.25)
            elif event_type == "region_assault_resumed":
                self._banner("region_resumed_banner", 1.0)
            elif event_type == "region_failed":
                self._finish_region_attempt(region_id, False)
                self._banner("region_failed_banner", 2.5)
            elif event_type == "region_cooldown_finished":
                self._queue_region_cleanup(region_id, "cooldown")
            elif event_type == "region_activated":
                completion_id = event["completionId"] + ":activated"
                if completion_id in self.objective_reward_receipts:
                    continue
                self.region_completion_order.append(region_id)
                self.global_threat_tier_elapsed = 0.0
                self._finish_region_attempt(region_id, True)
                self._banner("region_complete_banner", 2.7)
                if event.get("activationOrder") == 3:
                    HEngine.RuntimeResourceWarmup.QueueTrigger("FinalBoss")
                    self._prewarm_final_boss_effects()
                self.objective_reward_receipts.add(completion_id)
            elif event_type == "grant_domain_power":
                completion_id = event["completionId"] + ":domain"
                if completion_id in self.objective_reward_receipts:
                    continue
                domain_power_id = event["domainId"]
                self._grant_domain_power(self._runtime_domain_key(domain_power_id))
                bWasDiscovered = domain_power_id in self.profile.get(
                    "discoveredDomains", (),
                )
                bDiscovered = self._discover_domain(domain_power_id)
                if not bWasDiscovered and not bDiscovered:
                    # Persistence failed; the controller emits completion only
                    # once, so retain an explicit retry event.  The in-run
                    # combat grant above is itself idempotent.
                    self._queue_objective_retry_event(event)
                    continue
                if bDiscovered:
                    self.objective_newly_discovered_domains.add(domain_power_id)
                self.objective_reward_receipts.add(completion_id)
            elif event_type == "domain_overcharge":
                completion_id = event["completionId"] + ":overcharge"
                if completion_id in self.objective_reward_receipts:
                    continue
                self._trigger_domain_overcharge(
                    self._runtime_domain_key(event["domainId"]),
                    region_id,
                    player_pos,
                )
                self.objective_reward_receipts.add(completion_id)
            elif event_type == "vacuum_encounter_xp":
                completion_id = event["completionId"] + ":xp"
                if completion_id not in self.objective_reward_receipts:
                    self._vacuum_region_xp(region_id)
                    self.objective_reward_receipts.add(completion_id)
            elif event_type == "spawn_region_chest":
                completion_id = event["completionId"] + ":chest"
                if completion_id not in self.objective_reward_receipts:
                    self._queue_region_chest(event)
                    self.objective_reward_receipts.add(completion_id)
            elif event_type == "region_state_updated":
                completion_id = event["completionId"] + ":state"
                if completion_id in self.objective_reward_receipts:
                    continue
                if (
                        event["completionId"] + ":domain"
                        not in self.objective_reward_receipts):
                    self._queue_objective_retry_event(event)
                    continue
                if self.quest_tracker is not None:
                    domain_power_id = REGION_CONFIG[region_id]["domainId"]
                    self.quest_tracker.record(
                        "region_activated", 1, {"region": region_id},
                    )
                    if domain_power_id in self.objective_newly_discovered_domains:
                        self.objective_newly_discovered_domains.remove(domain_power_id)
                        self.quest_tracker.record(
                            "domain_discovered", 1,
                            {"domain": domain_power_id},
                        )
                self.objective_reward_receipts.add(completion_id)
            elif event_type == "retire_excess_region_monsters":
                self._queue_region_cleanup(region_id, "success")
            elif event_type == "boss_ready":
                self.global_spawn_suppression_remaining = max(
                    self.global_spawn_suppression_remaining,
                    float(event["suppressGlobalSpawnsSeconds"]),
                )
                self._play_central_summon_effect(0.55)
                self._banner("boss_ready_banner", 3.0)
            elif event_type == "boss_intro_started":
                self._play_central_summon_effect(0.85)
                self._banner("boss_intro_banner", 3.0)
            elif event_type == "boss_spawn_requested":
                self.pending_objective_boss_event = dict(event)

    def _begin_region_attempt(self, event, player_pos):
        region_id = event["regionId"]
        self.encounter_director.begin_attempt(
            region_id,
            int(event["attemptId"]),
            int(event["activationOrder"]),
            "region:" + region_id,
        )
        self.region_health_at_attempt_start[region_id] = float(self.health)
        self.region_fixed_elites_pending[region_id] = 0
        self.region_burst_spawns_pending[region_id] = 0
        self.region_kills_since_sample = 0
        self.region_sample_timer = 0.0
        self._retire_historical_tail(player_pos, region_id)
        HEngine.RuntimeResourceWarmup.QueueTrigger("RegionRewards")
        self._prewarm_region_reward_effects()

    @staticmethod
    def _prewarm_effect_paths(paths, label):
        for path in dict.fromkeys(paths):
            if not HEngine.VFX.LoadEffect(path):
                HEngine.HE_CORE_WARN(
                    "[SurvivorRegion] failed to preload " + label + " " + path,
                )

    def _prewarm_region_reward_effects(self):
        self._prewarm_effect_paths(
            (
                asset_path(asset_key)
                for config in DOMAIN_POWER_CONFIG.values()
                for role, asset_key in config["assetKeys"].items()
                if role != "icon"
            ),
            "DomainPower",
        )

    def _prewarm_final_boss_effects(self):
        self._prewarm_effect_paths((
            asset_path("objective/central-summon-vfx"),
            self.BOSS_SPAWN_WARNING_EFFECT,
            self.BOSS_AREA_TELEGRAPH_EFFECT,
        ), "FinalBoss")

    def _finish_region_attempt(self, region_id, success):
        starting_health = self.region_health_at_attempt_start.pop(
            region_id, float(self.health),
        )
        self.region_health_lost[region_id] += max(0.0, starting_health - self.health)
        if self.encounter_director.active_region_id == region_id:
            self.encounter_director.end_attempt(success)
        self.region_fixed_elites_pending[region_id] = 0
        self.region_burst_spawns_pending[region_id] = 0

    def _weighted_region_archetype(self, region_id, assault_elapsed):
        weights = region_roster_weights(region_id, assault_elapsed)
        total = sum(row["weight"] for row in weights)
        roll = self._random_uniform(0.0, total)
        cumulative = 0.0
        for row in weights:
            cumulative += row["weight"]
            if roll <= cumulative:
                return row["enemyId"]
        return weights[-1]["enemyId"]

    def _region_spawn_position(self, region_id, plan, player_pos):
        sockets = self.region_spawn_sockets.get(region_id, ())
        preferred = []
        for wave_event in plan.get("waveEvents", ()):
            preferred.extend(wave_event.get("socketIndices", ()))
        if preferred:
            index = preferred[self.region_spawn_serial % len(preferred)] % len(sockets)
        elif sockets:
            index = self.region_spawn_serial % len(sockets)
        else:
            self._record_spawn_failure("invalid_socket")
            return None
        self.region_spawn_serial += 1
        socket = sockets[index]
        grounded_y = self._try_grounded_y(
            HEngine.vec3(socket["x"], socket["y"] + 1.0, socket["z"]),
            self.MONSTER_GROUND_OFFSET,
        )
        if grounded_y is None:
            self._record_spawn_failure("ground_probe_failed")
            return None
        dx = socket["x"] - player_pos.x
        dz = socket["z"] - player_pos.z
        if dx * dx + dz * dz < 4.0 * 4.0:
            self._record_spawn_failure("too_close_to_player")
            return None
        return HEngine.vec3(socket["x"], grounded_y, socket["z"])

    def _local_region_alive(self, region_id):
        anchor = self.region_anchors[region_id][1].Translation
        center_x = float(anchor.x)
        center_z = float(anchor.z)
        radius = OBJECTIVE_CONFIG["localAliveRadius"]
        encounter_id = "region:" + region_id
        count = 0
        for _, entity_id, activation_id in HEngine.QuerySurvivorAgentsInRadius(
                center_x, 0.0, center_z, radius, 3.5e38):
            monster = self.monsters_by_id.get(entity_id)
            if (monster is not None
                    and not monster.get("dead", False)
                    and monster.get("activation_id") == activation_id
                    and monster.get("encounter_id") == encounter_id):
                count += 1
        if _LOCAL_ALIVE_VERIFY:
            rows = []
            for monster in self.monsters:
                position = monster["transform"].Translation
                rows.append({
                    "dead": monster.get("dead", False),
                    "encounterId": monster.get("encounter_id", ""),
                    "x": position.x,
                    "z": position.z,
                })
            expected = self.encounter_director.count_local_alive(
                rows, center_x, center_z, encounter_id, radius,
            )
            if count != expected:
                raise AssertionError(
                    "Native region alive count {} differs from reference {}".format(
                        count, expected,
                    )
                )
        return count

    def _spawn_region_pressure(self, region_id, region_state, player_pos, raw_dt):
        difficulty = getattr(
            getattr(self, "run_config", None),
            "selected_difficulty",
            "adventure",
        )
        challenge = self._challenge_tuning()
        local_alive = _timed_objective_call(
            "LocalAlive", self._local_region_alive, region_id,
        )
        total_alive = sum(1 for monster in self.monsters if not monster["dead"])
        self.encounter_director.record_kills(raw_dt, self.region_kills_since_sample)
        self.region_kills_since_sample = 0
        plan = self.encounter_director.plan_spawn(
            raw_dt,
            region_state["assaultElapsed"],
            local_alive,
            total_alive,
            difficulty,
            challenge,
            self.objective_controller.is_region_spawn_enabled(),
            len(self.region_spawn_sockets.get(region_id, ())),
        )
        self.region_last_plan = dict(plan)
        self.region_sample_timer -= raw_dt
        if self.region_sample_timer <= 0.0:
            self.region_sample_timer = self.REGION_TELEMETRY_SAMPLE_INTERVAL
            samples = self.region_local_alive_samples[region_id]
            samples.append({
                "elapsed": region_state["assaultElapsed"],
                "actual": local_alive,
                "target": plan["localTarget"],
                "spawnRate": plan["spawnRate"],
                "killsPerSecond": plan["recentKillsPerSecond"],
                "burstCount": int(plan["burstCount"]),
            })
            if len(samples) > 180:
                del samples[:len(samples) - 180]

        tier = ENCOUNTER_TIERS[
            max(0, min(3, self.encounter_director.activation_order - 1))
        ]
        fixed_elite_count = sum(
            int(row["count"]) for row in plan.get("fixedElites", ())
        )
        self.region_fixed_elites_pending[region_id] += fixed_elite_count
        pending_fixed_elites = self.region_fixed_elites_pending[region_id]
        burst_capacity = max(0, int(plan["missing"]) - pending_fixed_elites)
        self.region_burst_spawns_pending[region_id] = min(
            burst_capacity,
            self.region_burst_spawns_pending[region_id] + int(plan["burstCount"]),
        )
        pending_burst_spawns = self.region_burst_spawns_pending[region_id]
        self.region_last_plan["burstCount"] = int(plan["burstCount"])
        self.region_last_plan["burstPending"] = pending_burst_spawns
        regular_spawn_count = max(
            0,
            min(
                int(plan["spawnCount"]) - int(plan["burstCount"]),
                int(plan["missing"]) - pending_fixed_elites - pending_burst_spawns,
            ),
        )
        spawn_count = min(
            self.REGION_SPAWN_BUDGET_PER_FRAME,
            regular_spawn_count + pending_burst_spawns + pending_fixed_elites,
        )
        pressure_start_ns = time.perf_counter_ns() if _OBJECTIVE_TIMING_ENABLED else 0
        position_ms = 0.0
        activation_ms = 0.0
        activated_count = 0
        for _ in range(spawn_count):
            if sum(1 for monster in self.monsters if not monster["dead"]) >= self.MAX_MONSTERS:
                self._record_spawn_failure("global_cap")
                break
            position_start_ns = time.perf_counter_ns() if _OBJECTIVE_TIMING_ENABLED else 0
            spawn = self._region_spawn_position(region_id, plan, player_pos)
            if _OBJECTIVE_TIMING_ENABLED:
                position_ms += (time.perf_counter_ns() - position_start_ns) / 1_000_000.0
            if spawn is None:
                continue
            bFixedElite = self.region_fixed_elites_pending[region_id] > 0
            bBurstSpawn = (
                not bFixedElite and self.region_burst_spawns_pending[region_id] > 0
            )
            archetype_id = self._weighted_region_archetype(
                region_id, region_state["assaultElapsed"],
            )
            if bFixedElite:
                specialists = REGION_CONFIG[region_id]["specialists"]
                archetype_id = specialists[
                    self.region_spawn_serial % len(specialists)
                ]
            activation_start_ns = time.perf_counter_ns() if _OBJECTIVE_TIMING_ENABLED else 0
            activated = self._activate_monster(
                    spawn,
                    False,
                    self._current_wave_phase(),
                    archetype_id=archetype_id,
                    encounter_id="region:" + region_id,
                    zone_id=region_id,
                    attempt_id=int(region_state["attempts"]),
                    health_multiplier=tier["healthMultiplier"],
                    damage_multiplier=tier["damageMultiplier"],
                    reward_scale=0.50,
                    force_elite=bFixedElite,
                    fixed_elite=bFixedElite,
                    no_distance_retire=True)
            if _OBJECTIVE_TIMING_ENABLED:
                activation_ms += (time.perf_counter_ns() - activation_start_ns) / 1_000_000.0
            if not activated:
                self._record_spawn_failure("instantiate_failed")
            else:
                activated_count += 1
                spawned = self.monsters[-1]
                if spawned.get("elite", False):
                    if bFixedElite:
                        self.region_fixed_elites_pending[region_id] -= 1
                    target = (
                        self.region_fixed_elites_spawned
                        if bFixedElite else
                        self.region_random_elites_spawned
                    )
                    target[region_id] += 1
                if bBurstSpawn:
                    self.region_burst_spawns_pending[region_id] -= 1
        if _OBJECTIVE_TIMING_ENABLED and spawn_count > 0:
            total_ms = (time.perf_counter_ns() - pressure_start_ns) / 1_000_000.0
            if total_ms > 3.0:
                HEngine.HE_CORE_INFO(
                    "[RegionPressureTiming] elapsed={:.3f} planned={} activated={} totalMs={:.3f} positionMs={:.3f} activationMs={:.3f}".format(
                        self.elapsed, spawn_count, activated_count, total_ms,
                        position_ms, activation_ms,
                    )
                )

    def _consume_region_xp_reward(self, region_id, requested):
        if not region_id:
            return 0
        if self.encounter_director.active_region_id == region_id:
            self.region_kills_since_sample += 1
        return self.encounter_director.consume_xp(
            region_id, max(0.0, float(requested)),
        )

    def _consume_region_gold_reward(self, region_id, requested, _fixed=False):
        if not region_id:
            return 0
        return self.encounter_director.consume_gold(region_id, max(0, int(requested)))

    def _record_spawn_failure(self, reason):
        normalized = reason
        if reason.startswith("world_"):
            normalized = "ground_probe_failed"
        try:
            self.encounter_director.record_spawn_failure(normalized)
        except ValueError:
            HEngine.HE_CORE_WARN("[SurvivorRegion] unknown spawn failure " + reason)
        else:
            HEngine.HE_CORE_WARN("[SurvivorRegion] spawn skipped reason=" + reason)

    def _queue_region_chest(self, event):
        region_id = event["regionId"]
        position = self.region_anchors[region_id][1].Translation
        self.pending_chest_rewards.append({
            "sourceKind": event["sourceKind"],
            "sourceId": event["completionId"],
            "zoneId": event["zoneId"],
            "tier": int(event["tier"]),
            "position": (position.x, position.y, position.z),
        })

    def _vacuum_region_xp(self, region_id):
        encounter_id = "region:" + region_id
        for pickup in tuple(self.pickups):
            source_values = pickup.get("source_values")
            if isinstance(source_values, dict):
                region_value = float(source_values.get(encounter_id, 0.0))
            else:
                region_value = (
                    float(pickup["value"])
                    if pickup.get("encounter_id") == encounter_id else 0.0
                )
            if region_value <= 0.0:
                continue
            if region_value >= float(pickup["value"]):
                self._collect_pickup(pickup)
                continue
            pickup["value"] -= region_value
            source_values.pop(encounter_id, None)
            remaining_ids = tuple(source_values)
            if len(remaining_ids) == 1:
                pickup["encounter_id"] = remaining_ids[0]
                pickup["source_kind"] = (
                    "world" if remaining_ids[0] == "" else "region"
                )
            else:
                pickup["encounter_id"] = ""
                pickup["source_kind"] = "mixed"
            self.collected_shards += region_value
            self.score += int(round(region_value * 5))
            if self.quest_tracker is not None:
                self.quest_tracker.record("xp_collected", region_value)
            self._add_experience(region_value)
        retained = []
        for pending in self.pending_pickup_spawns:
            pending_encounter = pending[5] if len(pending) > 5 else ""
            if pending_encounter != encounter_id:
                retained.append(pending)
                continue
            value = pending[3]
            self.collected_shards += value
            self.score += int(round(value * 5))
            if self.quest_tracker is not None:
                self.quest_tracker.record("xp_collected", value)
            self._add_experience(value)
        self.pending_pickup_spawns = retained

    def _queue_region_cleanup(self, region_id, reason):
        key = (region_id, reason)
        if key not in self.region_cleanup_queue:
            self.region_cleanup_queue.append(key)

    def _progress_region_cleanup(self, player_pos):
        if not self.region_cleanup_queue:
            return
        region_id, reason = self.region_cleanup_queue[0]
        candidates = [
            monster for monster in self.monsters
            if not monster.get("dead", False)
            and monster.get("zone_id") == region_id
            and monster.get("region_spawned", False)
        ]
        retired = 0
        for monster in tuple(candidates):
            position = monster["transform"].Translation
            dx = position.x - player_pos.x
            dz = position.z - player_pos.z
            distance_sq = dx * dx + dz * dz
            bEngaged = bool(monster.get("attacking", False)) or distance_sq < 12.0 * 12.0
            if (
                    distance_sq >= OBJECTIVE_CONFIG["cleanupDistance"] ** 2
                    or (not bEngaged and distance_sq >= 12.0 * 12.0)):
                self._retire_monster(monster)
                retired += 1
                if retired >= self.REGION_CLEANUP_BUDGET_PER_FRAME:
                    break
            elif reason in ("cooldown", "success"):
                # Converted wanderers retain immutable reward provenance.  A
                # retry therefore counts them in localAlive and their eventual
                # drops/elite task credit still consume this Region's shared
                # run budget.
                monster["region_spawned"] = False
                set_retirement = getattr(
                    HEngine, "SetSurvivorAgentDistanceRetirement", None,
                )
                if set_retirement is not None:
                    set_retirement(
                        monster["entity"],
                        True,
                        monster.get("activation_id", 0),
                    )
        remaining = any(
            not monster.get("dead", False)
            and monster.get("zone_id") == region_id
            and monster.get("region_spawned", False)
            for monster in self.monsters
        )
        if not remaining:
            self.region_cleanup_queue.pop(0)

    def _retire_historical_tail(self, player_pos, active_region_id=None):
        if active_region_id is not None:
            self.region_historical_tail_cleanup = {
                "regionId": active_region_id,
                "maxActivationId": self.monster_activation_serial,
            }
        cleanup = self.region_historical_tail_cleanup
        if cleanup is None:
            return
        retired = 0
        for monster in tuple(self.monsters):
            if monster.get("dead", False) or monster.get("boss", False):
                continue
            if monster.get("activation_id", 0) > cleanup["maxActivationId"]:
                continue
            position = monster["transform"].Translation
            dx = position.x - player_pos.x
            dz = position.z - player_pos.z
            if dx * dx + dz * dz <= 32.0 * 32.0:
                continue
            self._retire_monster(monster)
            retired += 1
            if retired >= 16:
                break
        remaining = any(
            not monster.get("dead", False)
            and not monster.get("boss", False)
            and monster.get("activation_id", 0) <= cleanup["maxActivationId"]
            and (
                (monster["transform"].Translation.x - player_pos.x) ** 2
                + (monster["transform"].Translation.z - player_pos.z) ** 2
                > 32.0 * 32.0
            )
            for monster in self.monsters
        )
        if not remaining:
            self.region_historical_tail_cleanup = None

    def _global_population_target(self):
        snapshot = self.objective_controller.snapshot()
        state = snapshot["objectiveState"]
        if state in (OBJECTIVE_BOSS_READY, OBJECTIVE_BOSS_INTRO):
            return 35 if self.global_spawn_suppression_remaining <= 0.0 else 0
        if state == OBJECTIVE_BOSS_ACTIVE:
            boss = self.objective_boss
            if boss is None or boss.get("dead", False):
                return 40
            ratio = boss["health"] / max(1.0, boss["max_health"])
            return 40 if ratio > 0.66 else (70 if ratio > 0.33 else 100)
        band_progress = min(1.0, self.global_threat_tier_elapsed / 45.0)
        return global_threat_target(snapshot["completedCount"], band_progress)

    def _region_capacity_reserve(self):
        if not self.objective_controller.is_region_spawn_enabled():
            return 0
        return min(240, int(self.region_last_plan.get("localTarget", 50)))

    def _global_spawning_suppressed(self):
        return (
            self.global_spawn_suppression_remaining > 0.0
            or self.objective_controller.objective_state == OBJECTIVE_BOSS_INTRO
        )

    def _find_global_spawn_position(self, player_pos, event_id):
        if event_id:
            try:
                wave = resolve_wave_event(event_id, 8, int(self.elapsed))
            except ValueError:
                wave = None
            if wave is not None and wave["socketIndices"]:
                index = wave["socketIndices"][self.region_spawn_serial % len(wave["socketIndices"])]
                self.region_spawn_serial += 1
                angle = math.tau * index / 8.0
                distance = 12.0
                x = player_pos.x + math.cos(angle) * distance
                z = player_pos.z + math.sin(angle) * distance
                if abs(x) <= self.PLAYABLE_HALF_EXTENT and abs(z) <= self.PLAYABLE_HALF_EXTENT:
                    y = self._try_grounded_y(
                        HEngine.vec3(x, player_pos.y, z), self.MONSTER_GROUND_OFFSET,
                    )
                    if y is not None:
                        return HEngine.vec3(x, y, z)
        return self._find_spawn_position(player_pos)

    def _play_central_summon_effect(self, scale):
        position = self.objective_central_transform.Translation
        HEngine.VFX.PlayEffectAdvanced(
            asset_path("objective/central-summon-vfx"),
            position.x, position.y + 0.05, position.z,
            0.0, 0.0, -1.0,
            scale, 1.0, 0,
        )

    def _final_boss_warmup_ready(self):
        progress = HEngine.RuntimeResourceWarmup.GetTriggerProgress("FinalBoss")
        if progress is None:
            raise RuntimeError("FinalBoss resource warm-up trigger is not configured")
        if progress.FailedGroups > 0:
            HEngine.RuntimeResourceWarmup.RethrowFailure("FinalBoss")
        return progress.ReadyGroups == progress.TotalGroups

    def _make_objective_boss_capacity(self):
        alive = [monster for monster in self.monsters if not monster.get("dead", False)]
        required = max(0, len(alive) - self.MAX_MONSTERS + 1)
        if required <= 0:
            return True
        center = self.objective_central_transform.Translation
        candidates = [monster for monster in alive if not monster.get("boss", False)]
        candidates.sort(key=lambda monster: (
            bool(monster.get("attacking", False)),
            -(
                (monster["transform"].Translation.x - center.x) ** 2
                + (monster["transform"].Translation.z - center.z) ** 2
            ),
        ))
        for monster in candidates[:min(required, self.REGION_CLEANUP_BUDGET_PER_FRAME)]:
            self._retire_monster(monster)
        return sum(
            1 for monster in self.monsters if not monster.get("dead", False)
        ) < self.MAX_MONSTERS

    def _try_spawn_pending_objective_boss(self):
        event = self.pending_objective_boss_event
        if event is None or not self._final_boss_warmup_ready():
            return
        if self.objective_controller.objective_boss_spawned:
            self.pending_objective_boss_event = None
            return
        if not self._make_objective_boss_capacity():
            self._record_spawn_failure("global_cap")
            return
        difficulty = getattr(
            getattr(self, "run_config", None), "selected_difficulty", "adventure",
        )
        health_by_difficulty = {
            "adventure": 50000.0,
            "fierce": 75000.0,
            "nightmare": 110000.0,
        }
        position = self.objective_central_transform.Translation
        spawn = HEngine.vec3(position.x, position.y + 0.08, position.z)
        if not self._activate_monster(
                spawn,
                True,
                self._current_wave_phase(),
                archetype_id=event["archetypeId"],
                boss_event_id=event["eventId"],
                objective_boss=True,
                final_boss=True,
                max_health_override=health_by_difficulty[difficulty]):
            # Keep the explicit request pending.  Capacity retirement and pool
            # availability are retried on the next gameplay frame.
            return
        boss = self.monsters[-1]
        if not self.objective_controller.mark_boss_spawned(
                event["eventId"],
                boss["entity_id"],
                boss["activation_id"],
                boss["archetype_id"]):
            self._retire_monster(boss)
            raise RuntimeError("Objective Boss identity registration was rejected")
        self.pending_objective_boss_event = None
        self.objective_boss = boss
        capture_phase = os.environ.get("HE_SURVIVOR_CAPTURE_BOSS_PHASE", "").strip()
        if capture_phase in ("2", "3"):
            ratio = 0.60 if capture_phase == "2" else 0.25
            boss["health"] = boss["max_health"] * ratio
            set_health = getattr(HEngine, "SetSurvivorAgentHealth", None)
            if set_health is not None:
                set_health(
                    boss["entity"], boss["health"], boss.get("activation_id", 0),
                )
        self.objective_boss_spawn_raw_time = self.objective_controller.raw_elapsed
        self.objective_boss_phase = 1
        self.objective_boss_phase_started = 0.0
        self.objective_boss_ttk = 0.0
        if os.environ.get("HE_SURVIVOR_CAPTURE_FINAL_BOSS_HP", "0") == "1":
            boss["health"] = 0.0
            self._kill_monster(boss)

    def _on_objective_boss_killed(self, monster):
        accepted = self.objective_controller.mark_boss_killed(
            monster.get("boss_event_id", ""),
            monster.get("objective_boss", False),
            monster.get("entity_id"),
            monster.get("activation_id"),
            monster.get("archetype_id", ""),
            monster.get("final_boss", False),
        )
        if accepted:
            self.objective_boss_ttk = max(
                0.0,
                self.objective_controller.raw_elapsed
                - float(self.objective_boss_spawn_raw_time or 0.0),
            )
        return accepted

    def _on_objective_revive(self):
        events = self.objective_controller.on_revive()
        player_pos = self.player.GetComponent("Transform").Translation
        self._process_objective_events(events, player_pos)

    def _update_objective_boss_runtime(self, player_pos, raw_dt):
        boss = self.objective_boss
        if boss is None or boss.get("dead", False):
            return
        self.objective_boss_ttk = max(
            0.0,
            self.objective_controller.raw_elapsed
            - float(self.objective_boss_spawn_raw_time or 0.0),
        )
        ratio = boss["health"] / max(1.0, boss["max_health"])
        phase = 1 if ratio > 0.66 else (2 if ratio > 0.33 else 3)
        self.objective_boss_phase_durations[self.objective_boss_phase] += raw_dt
        if phase != self.objective_boss_phase:
            self.objective_boss_phase = phase
            self.objective_boss_phase_started = self.objective_boss_ttk
            self.pending_boss_domain_responses = list(self.domain_power_order)
            self.domain_global_vfx_spacing = 0.0
        if self.objective_boss_ttk >= 120.0:
            self.objective_boss_enraged = True

        center = self.objective_central_transform.Translation
        player_dx = player_pos.x - center.x
        player_dz = player_pos.z - center.z
        if player_dx * player_dx + player_dz * player_dz <= self.BOSS_LEASH_START_DISTANCE ** 2:
            return
        position = boss["transform"].Translation
        dx = center.x - position.x
        dz = center.z - position.z
        length = max(0.001, math.sqrt(dx * dx + dz * dz))
        step = min(length, self.BOSS_LEASH_RETURN_SPEED * raw_dt)
        position.x += dx / length * step
        position.z += dz / length * step
        boss["transform"].Translation = position
        if boss["health"] < boss["max_health"]:
            boss["health"] = min(
                boss["max_health"],
                boss["health"]
                + boss["max_health"] * self.BOSS_LEASH_HEAL_PER_SECOND * raw_dt,
            )
            set_health = getattr(HEngine, "SetSurvivorAgentHealth", None)
            if set_health is not None:
                set_health(
                    boss["entity"], boss["health"], boss.get("activation_id", 0),
                )

    def _update_boss_domain_responses(self):
        if not self.pending_boss_domain_responses or self.domain_global_vfx_spacing > 0.0:
            return
        domain_id = self.pending_boss_domain_responses.pop(0)
        boss = self.objective_boss
        if boss is None or boss.get("dead", False):
            self.pending_boss_domain_responses = []
            return
        position = boss["transform"].Translation
        config = DOMAIN_POWER_CONFIG[domain_id]
        HEngine.VFX.PlayEffectAdvanced(
            asset_path(config["assetKeys"]["castVfx"]),
            position.x, position.y + 0.10, position.z,
            0.0, 0.0, -1.0,
            0.12, 1.0, 0,
        )
        self.domain_global_vfx_spacing = self.DOMAIN_GLOBAL_VFX_SPACING

    def _update_objective_beacons(self, player_pos, raw_dt):
        self.region_visual_time += raw_dt
        visual_snapshot = self.objective_controller.snapshot()
        for region_id in REGION_IDS:
            region_row = visual_snapshot["regions"][region_id]
            state = region_row["state"]
            marker = self.region_markers[region_id][1]
            barrier = self.region_barriers[region_id][1]
            radius = REGION_CONFIG[region_id]["clearRadius"]
            pulse = 1.0
            rotation = 0.0
            barrier_scale = 0.001
            if state == REGION_ARMING:
                pulse = 1.0 + math.sin(self.region_visual_time * 4.0) * 0.018
                arming_progress = min(
                    1.0,
                    region_row["armingElapsed"]
                    / max(0.001, OBJECTIVE_CONFIG["armingSeconds"]),
                )
                barrier_scale = 0.28 + arming_progress * 0.72
            elif state in (REGION_ASSAULT, REGION_OUTSIDE_GRACE):
                rotation = self.region_visual_time * 0.35
                barrier_scale = (
                    0.96 + math.sin(self.region_visual_time * 6.0) * 0.04
                    if state == REGION_OUTSIDE_GRACE else
                    1.0 + math.sin(self.region_visual_time * 2.2) * 0.012
                )
            elif state == REGION_ACTIVATED:
                pulse = 1.018
            marker.Scale = HEngine.vec3(radius * pulse, 1.0, radius * pulse)
            marker.Rotation = HEngine.vec3(0.0, rotation, 0.0)
            barrier.Scale = HEngine.vec3(
                radius * barrier_scale,
                radius * 0.72 * barrier_scale,
                radius * barrier_scale,
            )
            barrier.Rotation = HEngine.vec3(0.0, -rotation * 0.55, 0.0)
        self.objective_beacon_timer -= raw_dt
        if self.objective_beacon_timer > 0.0:
            return
        self.objective_beacon_timer = 4.0 if self.particle_density == "low" else 2.5
        snapshot = self.objective_controller.snapshot()
        if snapshot["objectiveState"] in (OBJECTIVE_BOSS_READY, OBJECTIVE_BOSS_INTRO):
            self._play_central_summon_effect(0.32)
            return
        for region_id in REGION_IDS:
            state = snapshot["regions"][region_id]["state"]
            position = self.region_anchors[region_id][1].Translation
            config = DOMAIN_POWER_CONFIG[REGION_CONFIG[region_id]["domainId"]]
            scale = (
                0.08 if state == REGION_ACTIVATED else
                (0.10 if state == REGION_DORMANT else 0.14)
            )
            HEngine.VFX.PlayEffectAdvanced(
                asset_path(config["assetKeys"]["castVfx"]),
                position.x, position.y + 0.05, position.z,
                0.0, 1.0, 0.0,
                scale, 0.75, 0,
            )

    def _update_region_objectives(self, player_pos, raw_dt):
        global _OBJECTIVE_TIMING_SAMPLES
        objective_start_ns = time.perf_counter_ns() if _OBJECTIVE_TIMING_ENABLED else 0
        raw_dt = max(0.0, float(raw_dt))
        if self.pending_objective_retry_events:
            retry_events = tuple(self.pending_objective_retry_events)
            self.pending_objective_retry_events = []
            self._process_objective_events(retry_events, player_pos)
        self.global_spawn_suppression_remaining = max(
            0.0, self.global_spawn_suppression_remaining - raw_dt,
        )
        self.global_threat_tier_elapsed += raw_dt
        events = _timed_objective_call("Controller", self.objective_controller.update,
            raw_dt, player_pos.x, player_pos.z, gameplay_active=True,
        )
        self._process_objective_events(events, player_pos)
        region_id, region_state = self._active_region_snapshot()
        if region_id is not None and region_state["state"] == REGION_ASSAULT:
            _timed_objective_call(
                "Pressure", self._spawn_region_pressure,
                region_id, region_state, player_pos, raw_dt,
            )
        elif self.encounter_director.active_region_id is not None:
            # Grace and cooldown retain monsters but never add Region spawns.
            self.encounter_director.record_kills(raw_dt, self.region_kills_since_sample)
            self.region_kills_since_sample = 0
        _timed_objective_call("Cleanup", self._progress_region_cleanup, player_pos)
        _timed_objective_call("HistoricalTail", self._retire_historical_tail, player_pos)
        self._try_spawn_pending_objective_boss()
        self._update_boss_domain_responses()
        _timed_objective_call("Beacons", self._update_objective_beacons, player_pos, raw_dt)
        _timed_objective_call("Diagnostic", self._publish_objective_diagnostic)
        if _OBJECTIVE_TIMING_ENABLED:
            elapsed_ms = (time.perf_counter_ns() - objective_start_ns) / 1_000_000.0
            _OBJECTIVE_TIMING_TOTALS["Total"] = (
                _OBJECTIVE_TIMING_TOTALS.get("Total", 0.0) + elapsed_ms
            )
            _OBJECTIVE_TIMING_PEAKS["Total"] = max(
                _OBJECTIVE_TIMING_PEAKS.get("Total", 0.0), elapsed_ms,
            )
            _OBJECTIVE_TIMING_SAMPLES += 1
            if _OBJECTIVE_TIMING_SAMPLES == 60:
                details = " ".join(
                    "{}={:.3f}/{:.3f}".format(
                        stage, total / _OBJECTIVE_TIMING_SAMPLES,
                        _OBJECTIVE_TIMING_PEAKS[stage],
                    )
                    for stage, total in sorted(_OBJECTIVE_TIMING_TOTALS.items())
                )
                HEngine.HE_CORE_INFO(
                    "[SurvivorObjectiveTiming] mean/max ms over 60 frames: " + details
                )
                _OBJECTIVE_TIMING_SAMPLES = 0
                _OBJECTIVE_TIMING_TOTALS.clear()
                _OBJECTIVE_TIMING_PEAKS.clear()

    def _publish_objective_diagnostic(self):
        global _CURRENT_OBJECTIVE_DIAGNOSTIC
        objective = self.objective_controller.snapshot()
        encounter = self.encounter_director.snapshot()
        frame_values = sorted(getattr(self.telemetry, "frames", ()))

        def percentile(fraction):
            if not frame_values:
                return 0.0
            index = min(
                len(frame_values) - 1,
                int(round((len(frame_values) - 1) * fraction)),
            )
            return frame_values[index]

        _CURRENT_OBJECTIVE_DIAGNOSTIC = {
            "objectiveState": objective["objectiveState"],
            "activeRegion": objective["activeRegion"],
            "completedRegions": list(objective["completedRegions"]),
            "regionProgress": (
                0.0 if objective["activeRegion"] is None else
                objective["regions"][objective["activeRegion"]]["assaultElapsed"]
            ),
            "regionStates": objective["regions"],
            "localAlive": int(self.region_last_plan.get("localAlive", 0)),
            "localTarget": int(self.region_last_plan.get("localTarget", 0)),
            "regionSpawnRate": float(self.region_last_plan.get("spawnRate", 0.0)),
            "recentKillsPerSecond": float(
                self.region_last_plan.get("recentKillsPerSecond", 0.0)
            ),
            "spawnFailures": encounter["spawnFailures"],
            "encounterBudgets": encounter["budgets"],
            "domainCooldowns": self._domain_cooldown_snapshot(),
            "boss": {
                "ready": objective["objectiveState"] in (
                    OBJECTIVE_BOSS_READY, OBJECTIVE_BOSS_INTRO,
                    OBJECTIVE_BOSS_ACTIVE,
                ),
                "spawned": objective["bossSpawned"],
                "phase": self.objective_boss_phase,
                "ttk": self.objective_boss_ttk,
                "enraged": self.objective_boss_enraged,
            },
            "performance": {
                "frameMsP50": percentile(0.50),
                "frameMsP95": percentile(0.95),
                "frameMsP99": percentile(0.99),
                "peakMonsters": int(getattr(self.telemetry, "peak_monsters", 0)),
                "peakProjectiles": int(getattr(self.telemetry, "peak_projectiles", 0)),
                "peakVfx": int(getattr(self.telemetry, "peak_visuals", 0)),
                "animationBudget": self._animation_budget(),
            },
        }
        SurvivorSession.publish_objective_diagnostic(
            _CURRENT_OBJECTIVE_DIAGNOSTIC,
        )

    def _apply_objective_capture_scenario(self):
        scenario = os.environ.get("HE_SURVIVOR_CAPTURE_SCENARIO", "").strip().lower()
        if not scenario:
            return
        aliases = {
            "region_dormant": (0, None, 0.0),
            "region_1_assault_30": (0, "star", 30.0),
            "region_2_peak": (1, "thunder", 42.0),
            "region_3_peak": (2, "water", 42.0),
            "region_4_final": (3, "wind", 45.0),
            "region_grace": (0, "star", 30.0),
            "region_cooldown": (0, "star", 0.0),
            "boss_ready": (4, None, 0.0),
            "boss_phase_1": (4, None, 0.0),
            "boss_phase_2": (4, None, 0.0),
            "boss_phase_3": (4, None, 0.0),
            "three_slot_adventure": (0, None, 0.0),
            "six_slot_nightmare": (0, None, 0.0),
            "low_particle": (3, "wind", 50.0),
        }
        if scenario not in aliases:
            raise ValueError("Unknown HE_SURVIVOR_CAPTURE_SCENARIO: " + scenario)
        completed_count, active_region, progress = aliases[scenario]
        for region_id in REGION_IDS[:completed_count]:
            events = self.objective_controller.complete_region(region_id)
            # Fixtures need the same idempotent rewards, but no player is yet
            # available to process them here.  Queue the events for reset tail.
            self._process_objective_events(
                events, self.player.GetComponent("Transform").Translation,
            )
        if active_region is not None:
            anchor = self.region_anchors[active_region][1].Translation
            self.player.GetComponent("Transform").Translation = HEngine.vec3(
                anchor.x, anchor.y, anchor.z,
            )
            self.capture_player_position_override = HEngine.vec3(
                anchor.x, anchor.y, anchor.z,
            )
            arming_events = self.objective_controller.update(
                0.001, anchor.x, anchor.z,
            )
            self._process_objective_events(arming_events, anchor)
            start_events = self.objective_controller.update(1.5, anchor.x, anchor.z)
            self._process_objective_events(start_events, anchor)
            state = self.objective_controller.region_states[active_region]
            state.assault_elapsed = progress
            if scenario == "region_grace":
                state.state = REGION_OUTSIDE_GRACE
                state.grace_elapsed = 0.6
                outside_x = anchor.x + REGION_CONFIG[active_region]["holdRadius"] + 1.0
                outside = HEngine.vec3(outside_x, anchor.y, anchor.z)
                self.player.GetComponent("Transform").Translation = outside
                self.capture_player_position_override = outside
            elif scenario == "region_cooldown":
                state.state = REGION_COOLDOWN
                state.cooldown_remaining = 8.0
            self.capture_region_prefill_request = (
                active_region, progress, completed_count + 1,
            )
        if scenario.startswith("boss_phase_"):
            # Central hold/intro are stepped by the normal controller on the
            # first runtime frames; the capture HP override selects phase later.
            os.environ["HE_SURVIVOR_CAPTURE_BOSS_PHASE"] = scenario[-1]
        if scenario == "low_particle":
            self.particle_density = "low"

    def _apply_objective_capture_population(self):
        request = self.capture_region_prefill_request
        if request is None:
            return
        self.capture_region_prefill_request = None
        region_id, progress, activation_order = request
        difficulty = getattr(
            getattr(self, "run_config", None),
            "selected_difficulty",
            "adventure",
        )
        target = self.encounter_director.local_target(
            activation_order,
            min(1.0, max(0.0, progress / OBJECTIVE_CONFIG["assaultSeconds"])),
            difficulty,
            self._challenge_tuning(),
        )
        prefill_count = min(self.MAX_MONSTERS - 12, target)
        fixed_count = sum(
            row["count"] for row in self.encounter_director.fixed_elites_due(
                0.0, progress, activation_order,
            )
        )
        tier = ENCOUNTER_TIERS[max(0, min(3, activation_order - 1))]
        sockets = self.region_spawn_sockets[region_id]
        specialists = REGION_CONFIG[region_id]["specialists"]
        spawned_count = 0
        for index in range(prefill_count):
            socket = sockets[index % len(sockets)]
            ring = index // len(sockets)
            angle = socket["direction"] + math.pi * 0.5
            offset = ((ring % 7) - 3) * 0.18
            spawn = HEngine.vec3(
                socket["x"] + math.cos(angle) * offset,
                socket["y"],
                socket["z"] + math.sin(angle) * offset,
            )
            bFixedElite = index < fixed_count
            archetype_id = (
                specialists[index % len(specialists)]
                if bFixedElite else
                self._weighted_region_archetype(region_id, progress)
            )
            if not self._activate_monster(
                    spawn,
                    False,
                    self._current_wave_phase(),
                    archetype_id=archetype_id,
                    encounter_id="region:" + region_id,
                    zone_id=region_id,
                    attempt_id=int(
                        self.objective_controller.region_states[region_id].attempts
                    ),
                    health_multiplier=tier["healthMultiplier"],
                    damage_multiplier=tier["damageMultiplier"],
                    reward_scale=0.50,
                    force_elite=bFixedElite,
                    fixed_elite=bFixedElite,
                    no_distance_retire=True):
                self.region_fixed_elites_pending[region_id] += max(
                    0, fixed_count - min(index, fixed_count),
                )
                break
            spawned_count += 1
            if bFixedElite:
                self.region_fixed_elites_spawned[region_id] += 1
        HEngine.HE_CORE_INFO(
            "[SurvivorCapture] Region prefill " + region_id
            + " alive=" + str(spawned_count) + "/" + str(target),
        )

    def _sync_objective_hud(self, player_pos):
        snapshot = self.objective_controller.snapshot()
        panel_state = (
            snapshot["regions"][snapshot["activeRegion"]]["state"].lower()
            if snapshot["activeRegion"] is not None else
            snapshot["objectiveState"].lower()
        )
        for state_class in (
                "exploration", "region_assault", "dormant", "arming",
                "assault", "outside_grace", "cooldown", "activated",
                "boss_ready", "boss_intro", "boss_active", "victory"):
            self._set_hud_class(
                "region_objective_panel", state_class, panel_state == state_class,
            )
        self._set_hud_class(
            "hud", "particle_density_low", self.particle_density == "low",
        )
        self._set_hud_class(
            "hud", "low_particle", self.particle_density == "low",
        )
        self._set_hud_text(
            "region_completed_count",
            self._text("region_completed", count=snapshot["completedCount"]),
        )
        active_region = snapshot["activeRegion"]
        for region_id in REGION_IDS:
            self._set_hud_class(
                "region_objective_panel",
                "theme_" + region_id,
                active_region == region_id,
            )
        for region_id in REGION_IDS:
            row = snapshot["regions"][region_id]
            prefix = "region_seal_" + region_id
            for state in (
                    REGION_DORMANT, REGION_ARMING, REGION_ASSAULT,
                    REGION_OUTSIDE_GRACE, REGION_COOLDOWN, REGION_ACTIVATED):
                self._set_hud_class(prefix, state.lower(), row["state"] == state)
            anchor = self.region_anchors[region_id][1].Translation
            distance = math.sqrt(
                (anchor.x - player_pos.x) ** 2 + (anchor.z - player_pos.z) ** 2
            )
            direction = REGION_CONFIG[region_id]["direction"]
            self._set_hud_text(
                prefix + "_name", self._text("region_" + region_id + "_name"),
            )
            self._set_hud_text(
                prefix + "_status", self._text("region_state_" + row["state"].lower()),
            )
            self._set_hud_text(
                prefix + "_direction",
                "" if row["state"] == REGION_ACTIVATED else
                self._text(
                    "region_direction",
                    direction=self._text("direction_" + direction),
                    distance=int(distance),
                ),
            )
        if active_region is None:
            self._set_hud_text("region_current_name", self._text("region_explore_hint"))
            self._set_hud_text("region_countdown", "")
            self._set_hud_text(
                "region_status_instruction",
                self._text("region_explore_instruction"),
            )
            self._set_hud_style("region_progress_fill", "width", "0%")
        else:
            row = snapshot["regions"][active_region]
            self._set_hud_text(
                "region_current_name", self._text("region_" + active_region + "_name"),
            )
            if row["state"] == REGION_ARMING:
                arming_progress = min(
                    1.0,
                    row["armingElapsed"]
                    / max(0.001, OBJECTIVE_CONFIG["armingSeconds"]),
                )
                self._set_hud_text(
                    "region_countdown",
                    "%.1f" % max(
                        0.0,
                        OBJECTIVE_CONFIG["armingSeconds"] - row["armingElapsed"],
                    ),
                )
                self._set_hud_text(
                    "region_status_instruction",
                    self._text("region_arming_instruction"),
                )
                self._set_hud_style(
                    "region_progress_fill",
                    "width",
                    "%.2f%%" % (arming_progress * 100.0),
                )
            elif row["state"] in (REGION_ASSAULT, REGION_OUTSIDE_GRACE):
                remaining = max(0.0, row["assaultRemaining"])
                self._set_hud_text(
                    "region_countdown",
                    (
                        self._text(
                            "region_grace_countdown",
                            seconds="%.1f" % row["graceRemaining"],
                        )
                        if row["state"] == REGION_OUTSIDE_GRACE else
                        "%.1f" % remaining
                    ),
                )
                self._set_hud_text(
                    "region_status_instruction",
                    self._text(
                        "region_grace_instruction"
                        if row["state"] == REGION_OUTSIDE_GRACE else
                        "region_hold_instruction"
                    ),
                )
                self._set_hud_style(
                    "region_progress_fill",
                    "width",
                    "%.2f%%" % (
                        row["assaultElapsed"]
                        / max(0.001, OBJECTIVE_CONFIG["assaultSeconds"])
                        * 100.0
                    ),
                )
            elif row["state"] == REGION_COOLDOWN:
                self._set_hud_text(
                    "region_countdown", "%.1f" % row["cooldownRemaining"],
                )
                self._set_hud_text(
                    "region_status_instruction",
                    self._text("region_cooldown_instruction"),
                )
                self._set_hud_style("region_progress_fill", "width", "0%")
            else:
                self._set_hud_text("region_countdown", "")
                self._set_hud_text(
                    "region_status_instruction",
                    self._text("region_complete_instruction"),
                )
                self._set_hud_style("region_progress_fill", "width", "0%")

        objective_state = snapshot["objectiveState"]
        if objective_state in (OBJECTIVE_BOSS_READY, OBJECTIVE_BOSS_INTRO):
            center = self.objective_central_transform.Translation
            distance = math.sqrt(
                (center.x - player_pos.x) ** 2 + (center.z - player_pos.z) ** 2
            )
            self._set_hud_text(
                "objective_navigation",
                self._text("objective_return_center", distance=int(distance)),
            )
        elif objective_state == OBJECTIVE_BOSS_ACTIVE:
            self._set_hud_text("objective_navigation", self._text("objective_defeat_boss"))
        elif active_region is not None:
            active_state = snapshot["regions"][active_region]["state"]
            if active_state in (
                    REGION_ARMING, REGION_ASSAULT, REGION_OUTSIDE_GRACE):
                navigation_key = (
                    "objective_return_region"
                    if active_state == REGION_OUTSIDE_GRACE else
                    "objective_hold_region"
                )
                self._set_hud_text(
                    "objective_navigation",
                    self._text(
                        navigation_key,
                        region=self._text("region_" + active_region + "_name"),
                    ),
                )
            else:
                self._set_hud_text(
                    "objective_navigation", self._text("objective_find_regions"),
                )
        else:
            self._set_hud_text("objective_navigation", self._text("objective_find_regions"))

        cooldowns = self._domain_cooldown_snapshot()
        for domain_id, values in cooldowns.items():
            display_id = (
                domain_id[len("domain_"):]
                if domain_id.startswith("domain_") else
                domain_id
            )
            prefix = "domain_power_" + display_id
            self._set_hud_class(prefix, "locked", not values["acquired"])
            self._set_hud_class(prefix, "acquired", values["acquired"])
            self._set_hud_class(prefix, "ready", values["acquired"] and values["remaining"] <= 0.0)
            self._set_hud_text(
                prefix + "_cooldown",
                ("%.1f" % values["remaining"]) if values["acquired"] else self._text("locked"),
            )
