import math
import os
import time

import HEngine

from SurvivorContent import WEAPON_DEFS


_STAGE_TIMING_ENABLED = os.environ.get("HE_SURVIVOR_STAGE_TIMINGS") == "1"


class SurvivorWeaponsMixin:
    def _has_evolution(self, weapon_id, evolution_id=None):
        active = getattr(self, "active_evolutions", {}).get(weapon_id)
        return active == evolution_id if evolution_id else active is not None

    def _weapon_candidates(self, origin_x, origin_y, origin_z, attack_range):
        candidates = []
        for distance_sq, entity_id, activation_id in (
                HEngine.QuerySurvivorAgentsInRadius(
                    origin_x,
                    origin_y,
                    origin_z,
                    attack_range,
                    self.WEAPON_VERTICAL_RANGE,
                )):
            monster = self._resolve_survivor_target(entity_id, activation_id)
            if monster is not None:
                candidates.append((distance_sq, monster))
        return candidates

    def _resolve_survivor_target(self, entity_id, activation_id):
        monster = self.monsters_by_id.get(entity_id)
        if (monster is None or
                monster["dead"] or
                monster.get("activation_id", -1) != activation_id):
            return None
        return monster

    def _nearest_weapon_target(self, origin_x, origin_y, origin_z, attack_range):
        candidates = self._weapon_candidates(
            origin_x,
            origin_y,
            origin_z,
            attack_range,
        )
        if not candidates:
            return None
        return min(candidates, key=lambda item: item[0])[1]

    @staticmethod
    def _rotated_direction(direction_x, direction_z, angle_radians):
        cosine = math.cos(angle_radians)
        sine = math.sin(angle_radians)
        return (
            direction_x * cosine - direction_z * sine,
            direction_x * sine + direction_z * cosine,
        )

    @staticmethod
    def _fan_angles(projectile_count, spread_radians):
        if projectile_count <= 1:
            return (0.0,)
        return tuple(
            -spread_radians * 0.5
            + spread_radians * index / (projectile_count - 1)
            for index in range(projectile_count)
        )

    @staticmethod
    def _projectile_event(
            event_time,
            target,
            damage,
            origin_x,
            origin_z,
            force,
            hit_scale,
            hit_effect=None,
            hit_speed=3.2,
            source_id=""):
        return {
            "time": event_time,
            "target": target,
            "activation_id": target.get("activation_id", -1),
            "damage": damage,
            "origin_x": origin_x,
            "origin_z": origin_z,
            "force": force,
            "hit_scale": hit_scale,
            "hit_effect": hit_effect,
            "hit_speed": hit_speed,
            "source_id": source_id,
            "done": False,
        }

    def _spawn_projectile(
            self,
            effect,
            origin_x,
            origin_y,
            origin_z,
            end_x,
            end_y,
            end_z,
            duration,
            scale,
            effect_speed,
            events,
            trajectory="linear",
            arc_height=0.0,
            visual_pitch=0.0,
            launch_delay=0.0,
            homing_target=None,
            return_to_player=False,
            return_y_offset=0.0,
            return_curve=0.0,
            return_curve_sign=1.0,
            sweep_targets=None,
            sweep_damage=0.0,
            sweep_radius=0.0,
            sweep_force=0.0,
            sweep_hit_scale=0.0,
            sweep_max_hits=0,
            visual_kind=None,
            visual_scale=0.20,
            source_id="",
            _retry_age=0.0):
        reservation = self.projectile_budget.reserve(True)
        if reservation == "retry":
            telemetry = self.weapon_telemetry.get(source_id)
            if telemetry is not None:
                telemetry["spawnRetries"] += 1
            if _retry_age < 0.35 and len(self.pending_projectile_spawns) < 128:
                request = dict(locals())
                request.pop("self", None)
                request.pop("reservation", None)
                request.pop("telemetry", None)
                request["_retry_age"] = _retry_age
                self.pending_projectile_spawns.append({
                    "age": _retry_age,
                    "request": request,
                })
                return False

            # A bounded retry that still cannot reserve a gameplay slot is
            # merged into its authored hit payload.  The cast remains visible
            # and damaging instead of silently disappearing after cooldown use.
            HEngine.VFX.PlayEffectAdvanced(
                effect,
                origin_x, origin_y, origin_z,
                end_x - origin_x, 0.0, end_z - origin_z,
                scale, effect_speed,
            )
            for event in events:
                target = event["target"]
                if (
                        not target["dead"]
                        and target.get("activation_id", -1)
                        == event["activation_id"]):
                    self._apply_weapon_damage(
                        target,
                        event["damage"],
                        event["origin_x"],
                        event["origin_z"],
                        event["force"],
                        True,
                        event.get("source_id", source_id),
                    )
            for target in list(sweep_targets or ())[:max(1, sweep_max_hits)]:
                self._apply_weapon_damage(
                    target,
                    sweep_damage,
                    origin_x,
                    origin_z,
                    sweep_force,
                    True,
                    source_id,
                )
            return False

        direction_x = end_x - origin_x
        direction_z = end_z - origin_z
        direction_length = (
            direction_x * direction_x + direction_z * direction_z
        ) ** 0.5
        if direction_length < 0.001:
            direction_x = 0.0
            direction_z = -1.0
            direction_length = 1.0
        forward_y = direction_length * visual_pitch
        launch_delay = max(0.0, launch_delay)
        handle = -1
        if launch_delay <= 0.0:
            handle = HEngine.VFX.PlayEffectAdvanced(
                effect,
                origin_x, origin_y, origin_z,
                direction_x, forward_y, direction_z,
                scale, effect_speed,
            )
        visual_entity = (
            self._acquire_projectile_visual(visual_kind)
            if reservation == "full" else
            None
        )
        if reservation == "full" and visual_entity is None:
            self.projectile_budget.visual_active = max(
                0,
                self.projectile_budget.visual_active - 1,
            )
        if reservation == "core_fallback":
            telemetry = self.weapon_telemetry.get(source_id)
            if telemetry is not None:
                telemetry["visualDegrades"] += 1
        self.active_projectiles.append({
            "effect": effect,
            "handle": handle,
            "origin_x": origin_x,
            "origin_y": origin_y,
            "origin_z": origin_z,
            "last_x": origin_x,
            "last_y": origin_y,
            "last_z": origin_z,
            "end_x": end_x,
            "end_y": end_y,
            "end_z": end_z,
            "age": -launch_delay,
            "duration": max(0.05, duration),
            "scale": scale,
            "effect_speed": effect_speed,
            "events": events,
            "trajectory": trajectory,
            "arc_height": arc_height,
            "visual_pitch": visual_pitch,
            "bLaunched": launch_delay <= 0.0,
            "visual_restart_timer": 0.0,
            "homing_target": homing_target,
            "homing_activation_id": (
                homing_target.get("activation_id", -1)
                if homing_target is not None else
                -1
            ),
            "homing_y_offset": (
                end_y - homing_target["transform"].Translation.y
                if homing_target is not None else
                0.0
            ),
            "return_to_player": return_to_player,
            "return_y_offset": return_y_offset,
            "return_curve": max(0.0, return_curve),
            "return_curve_sign": (
                -1.0 if return_curve_sign < 0.0 else 1.0
            ),
            "sweep_target_keys": {
                (target["entity_id"], target.get("activation_id", -1))
                for target in (sweep_targets or [])
            },
            "sweep_damage": sweep_damage,
            "sweep_radius": max(0.0, sweep_radius),
            "sweep_force": sweep_force,
            "sweep_hit_scale": max(0.0, sweep_hit_scale),
            "sweep_max_hits": max(0, sweep_max_hits),
            "sweep_outward_hits": set(),
            "sweep_return_hits": set(),
            "visual_kind": visual_kind,
            "visual_entity": visual_entity,
            "visual_scale": visual_scale,
            "source_id": source_id,
            "bBudgetVisual": visual_entity is not None,
        })
        if self.quest_tracker is not None and source_id:
            self.quest_tracker.record(
                "projectiles_spawned",
                1,
                {"weapon": source_id.split(":", 1)[0]},
            )
        return True

    def _update_projectile_retries(self, dt):
        pending = []
        bSlotAvailable = self.projectile_budget.gameplay_active < self.MAX_ACTIVE_PROJECTILES
        for entry in self.pending_projectile_spawns:
            entry["age"] += dt
            if not bSlotAvailable:
                entry["request"]["_retry_age"] = entry["age"]
                pending.append(entry)
                continue
            request = entry["request"]
            request["_retry_age"] = entry["age"]
            self._spawn_projectile(**request)
            bSlotAvailable = self.projectile_budget.gameplay_active < self.MAX_ACTIVE_PROJECTILES
        self.pending_projectile_spawns = pending

    def _acquire_projectile_visual(self, visual_kind):
        if visual_kind not in self.projectile_visual_pool:
            return None
        pool = self.projectile_visual_pool[visual_kind]
        if pool:
            return pool.pop()
        if len(self.projectile_visual_entities) >= self.MAX_PROJECTILE_VISUALS:
            return None
        prefab = {
            "bolt": self.STAR_BOLT_PREFAB,
            "wheel": self.STAR_WHEEL_PREFAB,
            "comet": self.COMET_CORE_PREFAB,
            "bubble": self.BUBBLE_CORE_PREFAB,
            "fireball": self.FIREBALL_CORE_PREFAB,
            "petal": self.PETAL_CORE_PREFAB,
            "needle": self.HONEY_NEEDLE_CORE_PREFAB,
            "spore": self.SPORECAP_CORE_PREFAB,
            "bell": self.PHANTOM_BELL_CORE_PREFAB,
            "anchor": self.CORAL_ANCHOR_CORE_PREFAB,
            "prism": self.PRISM_CORE_PREFAB,
            "acorn": self.ACORN_CORE_PREFAB,
            "frost": self.FROST_ORB_CORE_PREFAB,
            "yoyo": self.GRAVITY_YOYO_CORE_PREFAB,
        }[visual_kind]
        if _STAGE_TIMING_ENABLED:
            instantiate_start_ns = time.perf_counter_ns()
        entity = HEngine.Instantiate(prefab, HEngine.vec3(0.0, -100.0, 0.0))
        if _STAGE_TIMING_ENABLED:
            instantiate_ms = (time.perf_counter_ns() - instantiate_start_ns) / 1_000_000.0
            if instantiate_ms > 3.0:
                HEngine.HE_CORE_INFO(
                    "[SurvivorVisualSpike] kind={} instantiate={:.3f}ms".format(
                        visual_kind, instantiate_ms,
                    )
                )
        self.projectile_visual_entities.append(entity)
        return entity

    def _release_projectile_visual(self, projectile):
        entity = projectile.get("visual_entity")
        visual_kind = projectile.get("visual_kind")
        if entity is None or visual_kind not in self.projectile_visual_pool:
            return
        transform = entity.GetComponent("Transform")
        transform.Translation = HEngine.vec3(0.0, -100.0, 0.0)
        transform.Scale = self.HIDDEN_SCALE
        self.projectile_visual_pool[visual_kind].append(entity)
        projectile["visual_entity"] = None

    def _move_projectile_visual(self, projectile, x, y, z, direction_x, direction_z, fraction):
        entity = projectile.get("visual_entity")
        if entity is None:
            return
        transform = entity.GetComponent("Transform")
        transform.Translation = HEngine.vec3(x, y, z)
        scale = projectile["visual_scale"] * self._reach_multiplier()
        transform.Scale = HEngine.vec3(scale, scale, scale)
        yaw = math.atan2(direction_x, direction_z)
        visual_kind = projectile.get("visual_kind")
        if visual_kind == "wheel":
            # Rotate in the ground plane so the beveled star face stays readable
            # from the top-down camera while its thickness still catches light.
            transform.Rotation = HEngine.vec3(0.0, yaw + fraction * math.pi * 4.0, 0.0)
        elif visual_kind == "petal":
            transform.Rotation = HEngine.vec3(0.0, yaw + fraction * math.pi * 2.0, 0.0)
        elif visual_kind == "bubble":
            transform.Rotation = HEngine.vec3(
                fraction * math.pi * 1.5,
                yaw + fraction * math.pi,
                fraction * math.pi * 0.5,
            )
        else:
            transform.Rotation = HEngine.vec3(0.0, yaw, 0.0)

    def _apply_projectile_sweep(
            self,
            projectile,
            start_x,
            start_z,
            end_x,
            end_z,
            bReturning):
        if (projectile["sweep_damage"] <= 0.0 or
                projectile["sweep_radius"] <= 0.0 or
                projectile["sweep_max_hits"] <= 0):
            return

        hit_keys = (
            projectile["sweep_return_hits"]
            if bReturning else
            projectile["sweep_outward_hits"]
        )
        remaining_hits = projectile["sweep_max_hits"] - len(hit_keys)
        if remaining_hits <= 0:
            return

        segment_x = end_x - start_x
        segment_z = end_z - start_z
        segment_length_sq = segment_x * segment_x + segment_z * segment_z
        if segment_length_sq < 0.000001:
            return

        contacts = []
        for (
                along,
                entity_id,
                activation_id,
                target_x,
                target_y,
                target_z,
                _,
        ) in HEngine.QuerySurvivorAgentsInSweptCapsule(
                start_x,
                start_z,
                end_x,
                end_z,
                projectile["sweep_radius"],
        ):
            hit_key = (entity_id, activation_id)
            if hit_key not in projectile["sweep_target_keys"]:
                continue
            if hit_key in hit_keys:
                continue
            target = self._resolve_survivor_target(entity_id, activation_id)
            if target is not None:
                contacts.append((
                    along,
                    target,
                    hit_key,
                    target_x,
                    target_y,
                    target_z,
                ))

        for _, target, hit_key, _, _, _ in (
                contacts[:remaining_hits]):
            hit_keys.add(hit_key)
            self._apply_weapon_damage(
                target,
                projectile["sweep_damage"],
                start_x,
                start_z,
                projectile["sweep_force"],
                True,
                projectile.get("source_id", ""),
            )

    def _update_projectiles(self, player_pos, dt):
        active_projectiles = []
        transform_commands = []
        pending_transforms = []
        for projectile in self.active_projectiles:
            previous_age = projectile["age"]
            projectile["age"] += dt
            projectile["visual_restart_timer"] = max(
                0.0,
                projectile["visual_restart_timer"] - dt,
            )
            if projectile["age"] < 0.0:
                active_projectiles.append(projectile)
                continue

            homing_target = projectile["homing_target"]
            if (homing_target is not None and
                    not homing_target["dead"] and
                    homing_target.get("activation_id", -1) ==
                    projectile["homing_activation_id"]):
                homing_position = homing_target["transform"].Translation
                projectile["end_x"] = homing_position.x
                projectile["end_y"] = (
                    homing_position.y + projectile["homing_y_offset"]
                )
                projectile["end_z"] = homing_position.z

            duration = projectile["duration"]
            fraction = min(1.0, projectile["age"] / duration)

            if projectile["trajectory"] == "boomerang":
                if fraction <= 0.5:
                    path_fraction = fraction * 2.0
                    position_x = projectile["origin_x"] + (
                        projectile["end_x"] - projectile["origin_x"]
                    ) * path_fraction
                    position_y = projectile["origin_y"] + (
                        projectile["end_y"] - projectile["origin_y"]
                    ) * path_fraction
                    position_y += (
                        math.sin(path_fraction * math.pi) ** 2
                        * projectile["arc_height"]
                    )
                    position_z = projectile["origin_z"] + (
                        projectile["end_z"] - projectile["origin_z"]
                    ) * path_fraction
                    fallback_x = (
                        projectile["end_x"] - projectile["origin_x"]
                    )
                    fallback_z = (
                        projectile["end_z"] - projectile["origin_z"]
                    )
                else:
                    return_fraction = (fraction - 0.5) * 2.0
                    if projectile["return_to_player"]:
                        return_x = player_pos.x
                        return_y = (
                            player_pos.y + projectile["return_y_offset"]
                        )
                        return_z = player_pos.z
                    else:
                        return_x = projectile["origin_x"]
                        return_y = projectile["origin_y"]
                        return_z = projectile["origin_z"]
                    return_dx = return_x - projectile["end_x"]
                    return_dz = return_z - projectile["end_z"]
                    return_length = (
                        return_dx * return_dx + return_dz * return_dz
                    ) ** 0.5
                    launch_dx = projectile["end_x"] - projectile["origin_x"]
                    launch_dz = projectile["end_z"] - projectile["origin_z"]
                    launch_length = max(
                        0.001,
                        (launch_dx * launch_dx + launch_dz * launch_dz) ** 0.5,
                    )
                    launch_x = launch_dx / launch_length
                    launch_z = launch_dz / launch_length
                    curve_sign = projectile["return_curve_sign"]
                    normal_x = -launch_z * curve_sign
                    normal_z = launch_x * curve_sign
                    tangent_forward = min(2.0, launch_length * 0.32)
                    tangent_side = min(
                        projectile["return_curve"],
                        launch_length * 0.20,
                    )
                    start_tangent_x = (
                        launch_x * tangent_forward + normal_x * tangent_side
                    )
                    start_tangent_z = (
                        launch_z * tangent_forward + normal_z * tangent_side
                    )
                    if return_length >= 0.001:
                        return_direction_x = return_dx / return_length
                        return_direction_z = return_dz / return_length
                    else:
                        return_direction_x = -launch_x
                        return_direction_z = -launch_z
                    end_tangent_scale = min(2.0, return_length * 0.35)
                    end_tangent_x = return_direction_x * end_tangent_scale
                    end_tangent_z = return_direction_z * end_tangent_scale
                    fraction_sq = return_fraction * return_fraction
                    fraction_cube = fraction_sq * return_fraction
                    h00 = 2.0 * fraction_cube - 3.0 * fraction_sq + 1.0
                    h10 = fraction_cube - 2.0 * fraction_sq + return_fraction
                    h01 = -2.0 * fraction_cube + 3.0 * fraction_sq
                    h11 = fraction_cube - fraction_sq
                    position_x = (
                        h00 * projectile["end_x"]
                        + h10 * start_tangent_x
                        + h01 * return_x
                        + h11 * end_tangent_x
                    )
                    height_blend = fraction_sq * (3.0 - 2.0 * return_fraction)
                    position_y = projectile["end_y"] + (
                        return_y - projectile["end_y"]
                    ) * height_blend
                    position_y += (
                        math.sin(return_fraction * math.pi) ** 2
                        * projectile["arc_height"]
                    )
                    position_z = (
                        h00 * projectile["end_z"]
                        + h10 * start_tangent_z
                        + h01 * return_z
                        + h11 * end_tangent_z
                    )
                    derivative_h00 = 6.0 * fraction_sq - 6.0 * return_fraction
                    derivative_h10 = 3.0 * fraction_sq - 4.0 * return_fraction + 1.0
                    derivative_h01 = -derivative_h00
                    derivative_h11 = 3.0 * fraction_sq - 2.0 * return_fraction
                    fallback_x = (
                        derivative_h00 * projectile["end_x"]
                        + derivative_h10 * start_tangent_x
                        + derivative_h01 * return_x
                        + derivative_h11 * end_tangent_x
                    )
                    fallback_z = (
                        derivative_h00 * projectile["end_z"]
                        + derivative_h10 * start_tangent_z
                        + derivative_h01 * return_z
                        + derivative_h11 * end_tangent_z
                    )
            else:
                path_fraction = fraction
                arc_offset = math.sin(fraction * math.pi) * projectile["arc_height"]
                position_x = projectile["origin_x"] + (
                    projectile["end_x"] - projectile["origin_x"]
                ) * path_fraction
                position_y = projectile["origin_y"] + (
                    projectile["end_y"] - projectile["origin_y"]
                ) * path_fraction + arc_offset
                position_z = projectile["origin_z"] + (
                    projectile["end_z"] - projectile["origin_z"]
                ) * path_fraction
                fallback_x = projectile["end_x"] - projectile["origin_x"]
                fallback_z = projectile["end_z"] - projectile["origin_z"]

            # Face the actual velocity tangent instead of retaining the launch
            # heading. This keeps homing bolts aligned and naturally flips a
            # returning projectile as soon as it starts its way back.
            segment_start_x = projectile["last_x"]
            segment_start_z = projectile["last_z"]
            direction_x = position_x - segment_start_x
            direction_z = position_z - segment_start_z
            horizontal_length = (
                direction_x * direction_x + direction_z * direction_z
            ) ** 0.5
            if horizontal_length < 0.001:
                direction_x = fallback_x
                direction_z = fallback_z
                horizontal_length = (
                    direction_x * direction_x + direction_z * direction_z
                ) ** 0.5
            if horizontal_length < 0.001:
                direction_x = 0.0
                direction_z = -1.0
                horizontal_length = 1.0
            forward_y = horizontal_length * projectile["visual_pitch"]

            if projectile["sweep_damage"] > 0.0:
                previous_fraction = max(
                    0.0,
                    min(1.0, previous_age / duration),
                )
                if previous_fraction < 0.5 < fraction:
                    self._apply_projectile_sweep(
                        projectile,
                        segment_start_x,
                        segment_start_z,
                        projectile["end_x"],
                        projectile["end_z"],
                        False,
                    )
                    self._apply_projectile_sweep(
                        projectile,
                        projectile["end_x"],
                        projectile["end_z"],
                        position_x,
                        position_z,
                        True,
                    )
                else:
                    self._apply_projectile_sweep(
                        projectile,
                        segment_start_x,
                        segment_start_z,
                        position_x,
                        position_z,
                        fraction > 0.5,
                    )

            projectile["last_x"] = position_x
            projectile["last_y"] = position_y
            projectile["last_z"] = position_z
            self._move_projectile_visual(
                projectile,
                position_x, position_y, position_z,
                direction_x, direction_z,
                fraction,
            )

            for event in projectile["events"]:
                if event["done"] or projectile["age"] < event["time"]:
                    continue
                event["done"] = True
                target = event["target"]
                if (target["dead"] or
                        target.get("activation_id", -1) != event["activation_id"]):
                    continue

                self._apply_weapon_damage(
                    target,
                    event["damage"],
                    event["origin_x"],
                    event["origin_z"],
                    event["force"],
                    True,
                    event.get("source_id", ""),
                )

            if fraction < 1.0:
                if projectile["bLaunched"] and projectile["handle"] >= 0:
                    transform_commands.append((
                        projectile["handle"],
                        position_x, position_y, position_z,
                        direction_x, forward_y, direction_z,
                    ))
                    pending_transforms.append((
                        projectile,
                        position_x, position_y, position_z,
                        direction_x, forward_y, direction_z,
                    ))
                elif projectile["visual_restart_timer"] <= 0.0:
                    projectile["handle"] = HEngine.VFX.PlayEffectAdvanced(
                        projectile["effect"],
                        position_x, position_y, position_z,
                        direction_x, forward_y, direction_z,
                        projectile["scale"], projectile["effect_speed"],
                    )
                    projectile["bLaunched"] = True
                    projectile["visual_restart_timer"] = (
                        self.PROJECTILE_RESTART_INTERVAL
                    )
                active_projectiles.append(projectile)
            elif projectile["handle"] >= 0:
                HEngine.VFX.StopEffect(projectile["handle"])
                self.projectile_budget.release(
                    projectile.get("bBudgetVisual", False),
                )
                self._release_projectile_visual(projectile)
            elif fraction >= 1.0:
                self.projectile_budget.release(
                    projectile.get("bBudgetVisual", False),
                )
                self._release_projectile_visual(projectile)

        transform_results = (
            HEngine.VFX.SetEffectTransforms(transform_commands)
            if transform_commands else
            ()
        )
        for bMoved, pending in zip(transform_results, pending_transforms):
            if bMoved:
                continue
            (
                projectile,
                position_x, position_y, position_z,
                direction_x, forward_y, direction_z,
            ) = pending
            if projectile["visual_restart_timer"] > 0.0:
                continue
            projectile["handle"] = HEngine.VFX.PlayEffectAdvanced(
                projectile["effect"],
                position_x, position_y, position_z,
                direction_x, forward_y, direction_z,
                projectile["scale"], projectile["effect_speed"],
            )
            projectile["bLaunched"] = True
            projectile["visual_restart_timer"] = (
                self.PROJECTILE_RESTART_INTERVAL
            )

        self.active_projectiles = active_projectiles

    def _fire_thunder(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            self.thunder_timer = 0.08
            return

        strike_count = min(self._thunder_target_count(), len(candidates))
        for _ in range(strike_count):
            index = min(
                len(candidates) - 1,
                int(self._random_uniform(0.0, float(len(candidates)))),
            )
            target = candidates.pop(index)[1]
            target_pos = target["transform"].Translation
            hit_height = 0.58 if target["boss"] else 0.40
            HEngine.VFX.PlayEffectAdvanced(
                self.THUNDER_EFFECT,
                target_pos.x, target_pos.y + hit_height, target_pos.z,
                0.0, 0.0, -1.0,
                (0.16 if target["boss"] else 0.13) * self._reach_multiplier(),
                1.75,
            )
            self._apply_weapon_damage(
                target,
                self._thunder_damage(),
                player_pos.x,
                player_pos.z,
                self.knockback * 4.0,
                True,
                "thunder",
            )

        self.audio.weapon_cast("thunder", player_pos)
        self.thunder_timer = self._thunder_interval()

    def _fire_ring(self, player_pos):
        max_radius = self._ring_radius()
        if not self._weapon_candidates(
                player_pos.x,
                player_pos.y,
                player_pos.z,
                max_radius + 1.0):
            self.ring_timer = 0.12
            return

        HEngine.VFX.PlayEffectAdvanced(
            self.RING_EFFECT,
            player_pos.x, player_pos.y + 0.12, player_pos.z,
            0.0, 0.0, -1.0,
            max_radius / 3.0, self.RING_EFFECT_SPEED,
        )
        self.active_ring_waves.append({
            "origin_x": player_pos.x,
            "origin_y": player_pos.y,
            "origin_z": player_pos.z,
            "age": 0.0,
            "radius": 0.0,
            "max_radius": max_radius,
            "damage": self._ring_damage(),
            "hit_ids": set(),
        })
        self.audio.weapon_cast("ring", player_pos)
        self.ring_timer = self._ring_interval()

    def _update_ring_waves(self, dt):
        active_waves = []
        for wave in self.active_ring_waves:
            previous_radius = wave["radius"]
            wave["age"] += dt
            fraction = min(1.0, wave["age"] / self.RING_EXPANSION_TIME)
            wave["radius"] = wave["max_radius"] * fraction

            for _, entity_id, activation_id, _, _, _, _ in (
                    HEngine.QuerySurvivorAgentsInSweptAnnulus(
                        wave["origin_x"],
                        wave["origin_y"],
                        wave["origin_z"],
                        previous_radius,
                        wave["radius"],
                        self.RING_EDGE_WIDTH,
                        self.WEAPON_VERTICAL_RANGE,
                    )):
                if entity_id in wave["hit_ids"]:
                    continue
                monster = self._resolve_survivor_target(entity_id, activation_id)
                if monster is None:
                    continue
                wave["hit_ids"].add(entity_id)
                self._apply_weapon_damage(
                    monster,
                    wave["damage"],
                    wave["origin_x"],
                    wave["origin_z"],
                    0.0,
                    True,
                    "ring",
                )

            if fraction < 1.0:
                active_waves.append(wave)
        self.active_ring_waves = active_waves

    def _fire_fireball(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            self.fireball_timer = 0.10
            return

        candidates.sort(key=lambda item: item[0])
        for projectile_index, (_, target) in enumerate(
                candidates[:self._fireball_target_count()]):
            self._launch_fireball(
                player_pos,
                target,
                projectile_index * 0.08,
            )
        self.audio.weapon_cast("fireball", player_pos)
        self.fireball_timer = self._fireball_interval()

    def _launch_fireball(self, player_pos, target, launch_delay=0.0):
        target_pos = target["transform"].Translation
        to_player_x = player_pos.x - target_pos.x
        to_player_z = player_pos.z - target_pos.z
        horizontal_distance = max(
            0.001,
            (to_player_x * to_player_x + to_player_z * to_player_z) ** 0.5,
        )
        impact_time = self._projectile_travel_time(max(
            self.FIREBALL_MIN_TRAVEL_TIME,
            min(
                self.FIREBALL_MAX_TRAVEL_TIME,
                horizontal_distance / self.FIREBALL_TRAVEL_SPEED,
            ),
        ))
        stopping_distance = target["radius"] + 0.42
        predicted_travel = min(
            target["speed"] * (impact_time + launch_delay),
            max(0.0, horizontal_distance - stopping_distance),
        )
        impact_x = (
            target_pos.x
            + to_player_x / horizontal_distance * predicted_travel
        )
        impact_y = target_pos.y + (0.58 if target["boss"] else 0.40)
        impact_z = (
            target_pos.z
            + to_player_z / horizontal_distance * predicted_travel
        )
        direction_x = impact_x - player_pos.x
        direction_z = impact_z - player_pos.z
        direction_length = (
            direction_x * direction_x + direction_z * direction_z
        ) ** 0.5
        if direction_length < 0.001:
            direction_x = 0.0
            direction_z = 1.0
            direction_length = 1.0
        direction_x /= direction_length
        direction_z /= direction_length

        effect_origin_y = player_pos.y + 0.62
        launch_delay = max(0.0, launch_delay)
        handle = -1
        if launch_delay <= 0.0:
            handle = HEngine.VFX.PlayEffectAdvanced(
                self.FIREBALL_EFFECT,
                player_pos.x, effect_origin_y, player_pos.z,
                direction_x, 0.0, direction_z,
                self.FIREBALL_EFFECT_SCALE,
                1.0,
            )
        self.active_fireballs.append({
            "handle": handle,
            "bLaunched": handle >= 0,
            "retry_timer": self.FIREBALL_RETRY_INTERVAL if handle < 0 else 0.0,
            "age": -launch_delay,
            "impact_time": impact_time,
            "impact_x": impact_x,
            "impact_y": impact_y,
            "impact_z": impact_z,
            "origin_x": player_pos.x,
            "origin_y": effect_origin_y,
            "origin_z": player_pos.z,
            "root_end_x": impact_x,
            "root_end_y": impact_y,
            "root_end_z": impact_z,
            "direction_x": direction_x,
            "direction_z": direction_z,
            "arc_height": self.FIREBALL_ROOT_ARC_HEIGHT,
            "damage": self._fireball_damage(),
            "visual_kind": "fireball",
            "visual_entity": self._acquire_projectile_visual("fireball"),
            "visual_scale": 0.62,
        })
        if self.quest_tracker is not None:
            self.quest_tracker.record(
                "projectiles_spawned", 1, {"weapon": "fireball"},
            )

    def _update_fireballs(self, dt):
        prepared_fireballs = []
        transform_commands = []
        pending_transforms = []
        for fireball in self.active_fireballs:
            fireball["age"] += dt
            fireball["retry_timer"] = max(0.0, fireball["retry_timer"] - dt)
            if fireball["age"] < 0.0:
                prepared_fireballs.append((fireball, False))
                continue

            if not fireball["bLaunched"] and fireball["retry_timer"] <= 0.0:
                fireball["handle"] = HEngine.VFX.PlayEffectAdvanced(
                    self.FIREBALL_EFFECT,
                    fireball["origin_x"],
                    fireball["origin_y"],
                    fireball["origin_z"],
                    fireball["direction_x"],
                    0.0,
                    fireball["direction_z"],
                    self.FIREBALL_EFFECT_SCALE,
                    1.0,
                )
                fireball["bLaunched"] = fireball["handle"] >= 0
                if not fireball["bLaunched"]:
                    fireball["retry_timer"] = self.FIREBALL_RETRY_INTERVAL

            travel_fraction = min(
                1.0,
                fireball["age"] / fireball["impact_time"],
            )
            root_x = fireball["origin_x"] + (
                fireball["root_end_x"] - fireball["origin_x"]
            ) * travel_fraction
            root_y = fireball["origin_y"] + (
                fireball["root_end_y"] - fireball["origin_y"]
            ) * travel_fraction
            root_y += (
                math.sin(travel_fraction * math.pi) * fireball["arc_height"]
            )
            root_z = fireball["origin_z"] + (
                fireball["root_end_z"] - fireball["origin_z"]
            ) * travel_fraction
            if fireball["handle"] >= 0:
                transform_commands.append((
                    fireball["handle"],
                    root_x, root_y, root_z,
                    fireball["direction_x"], 0.0, fireball["direction_z"],
                ))
                pending_transforms.append(fireball)
            self._move_projectile_visual(
                fireball,
                root_x, root_y, root_z,
                fireball["direction_x"], fireball["direction_z"],
                travel_fraction,
            )
            prepared_fireballs.append((fireball, True))

        transform_results = (
            HEngine.VFX.SetEffectTransforms(transform_commands)
            if transform_commands else
            ()
        )
        for bMoved, fireball in zip(transform_results, pending_transforms):
            if bMoved:
                continue
            fireball["handle"] = -1
            fireball["bLaunched"] = False
            fireball["retry_timer"] = self.FIREBALL_RETRY_INTERVAL

        active_fireballs = []
        for fireball, bReady in prepared_fireballs:
            if not bReady:
                active_fireballs.append(fireball)
                continue
            if fireball["age"] < fireball["impact_time"]:
                active_fireballs.append(fireball)
                continue

            self._release_projectile_visual(fireball)
            if fireball["handle"] >= 0:
                HEngine.VFX.StopEffect(fireball["handle"])
            impact_target = None
            impact_row = HEngine.FindSurvivorAgentCircleOverlap(
                fireball["impact_x"],
                fireball["impact_y"],
                fireball["impact_z"],
                self._weapon_reach(self.FIREBALL_IMPACT_PADDING),
                self.WEAPON_VERTICAL_RANGE,
            )
            if impact_row is not None:
                impact_target = self._resolve_survivor_target(
                    impact_row[1],
                    impact_row[2],
                )

            if impact_target is not None:
                self._apply_weapon_damage(
                    impact_target,
                    fireball["damage"],
                    fireball["origin_x"],
                    fireball["origin_z"],
                    2.2 + self.fireball_level * 0.2,
                    True,
                    "fireball",
                )
        self.active_fireballs = active_fireballs

    def _fire_moonblade(self, player_pos):
        attack_range = self._weapon_reach(9.0)
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            attack_range,
        )
        if not candidates:
            self.moonblade_timer = 0.10
            return

        primary = min(candidates, key=lambda item: item[0])[1]
        primary_pos = primary["transform"].Translation
        aim_x = primary_pos.x - player_pos.x
        aim_z = primary_pos.z - player_pos.z
        aim_length = (aim_x * aim_x + aim_z * aim_z) ** 0.5
        if aim_length < 0.001:
            aim_x = 0.0
            aim_z = 1.0
            aim_length = 1.0
        aim_x /= aim_length
        aim_z /= aim_length

        moonblade_stats = self._catalog_weapon_stats("moonblade")
        projectile_count = moonblade_stats["amount"]
        spread = math.radians(12.0 if projectile_count == 2 else 24.0)
        travel_distance = self._weapon_reach(
            7.6 + (self.moonblade_level - 1) * 0.16,
        )
        duration = self._projectile_travel_time(0.72)
        projectile_directions = [
            self._rotated_direction(aim_x, aim_z, angle)
            for angle in self._fan_angles(projectile_count, spread)
        ]
        corridor_batches = HEngine.QuerySurvivorAgentCorridors(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            attack_range,
            self.WEAPON_VERTICAL_RANGE,
            [
                (
                    player_pos.x,
                    player_pos.z,
                    direction_x,
                    direction_z,
                    travel_distance,
                    self._weapon_reach(0.72),
                    min(12, max(1, moonblade_stats["pierce"])),
                )
                for direction_x, direction_z in projectile_directions
            ],
        )
        for projectile_index, ((direction_x, direction_z), hit_rows) in enumerate(
                zip(projectile_directions, corridor_batches)):
            corridor_hits = []
            for along, entity_id, activation_id, _, _, _, _ in hit_rows:
                target = self._resolve_survivor_target(entity_id, activation_id)
                if target is not None:
                    corridor_hits.append((along, target))
            events = [
                self._projectile_event(
                    max(0.04, duration * along / travel_distance),
                    target,
                    self._moonblade_damage(),
                    player_pos.x,
                    player_pos.z,
                    1.2,
                    0.10 * self._reach_multiplier(),
                    source_id="moonblade",
                )
                for along, target in corridor_hits
            ]
            self._spawn_projectile(
                self.MOONBLADE_EFFECT,
                player_pos.x,
                player_pos.y + 0.55,
                player_pos.z,
                player_pos.x + direction_x * travel_distance,
                player_pos.y + 0.55,
                player_pos.z + direction_z * travel_distance,
                duration,
                self.MOONWAVE_PROJECTILE_SCALE * self._reach_multiplier(),
                1.0,
                events,
                arc_height=0.08,
                visual_pitch=0.0,
                launch_delay=projectile_index * 0.055,
                visual_kind="bolt",
                visual_scale=0.20,
                source_id="moonblade",
            )
        self.audio.weapon_cast("moonblade", player_pos)
        self.moonblade_timer = self._moonblade_interval()

    def _fire_bubble(self, player_pos):
        bubble_stats = self._catalog_weapon_stats("bubble")
        bounce_count = min(12, max(1, bubble_stats["bounce"] + 1))
        target_rows = HEngine.SelectSurvivorAgentChain(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            self._weapon_reach(3.8),
            bounce_count,
        )
        chain_targets = []
        for _, entity_id, activation_id, _, _, _, _ in target_rows:
            target = self._resolve_survivor_target(entity_id, activation_id)
            if target is not None:
                chain_targets.append((target, activation_id))
        if not chain_targets:
            self.bubble_timer = 0.10
            return

        self.active_bubble_chains.append({
            "targets": chain_targets,
            "index": 0,
            "timer": 0.0,
            "origin_x": player_pos.x,
            "origin_y": player_pos.y + 0.42,
            "origin_z": player_pos.z,
            "origin_target": None,
            "origin_activation_id": -1,
            "damage": self._bubble_damage(),
        })
        self.audio.weapon_cast("bubble", player_pos)
        if self._has_evolution("bubble", "royalbubblecade"):
            self.character_hook_state["royalBubbleProjectileShield"] = 1
        self.bubble_timer = self._bubble_interval()

    def _update_bubble_chains(self, dt):
        active_chains = []
        for chain in self.active_bubble_chains:
            chain["timer"] -= dt
            if chain["timer"] > 0.0:
                active_chains.append(chain)
                continue

            targets = chain["targets"]
            while chain["index"] < len(targets):
                pending_target, activation_id = targets[chain["index"]]
                if (not pending_target["dead"] and
                        pending_target.get("activation_id", -1) == activation_id):
                    break
                chain["index"] += 1
            if chain["index"] >= len(targets):
                continue

            origin_target = chain["origin_target"]
            if (origin_target is not None and
                    not origin_target["dead"] and
                    origin_target.get("activation_id", -1) ==
                    chain["origin_activation_id"]):
                origin_pos = origin_target["transform"].Translation
                chain["origin_x"] = origin_pos.x
                chain["origin_y"] = (
                    origin_pos.y + (0.52 if origin_target["boss"] else 0.32)
                )
                chain["origin_z"] = origin_pos.z

            target, _ = targets[chain["index"]]
            target_pos = target["transform"].Translation
            target_y = target_pos.y + (0.52 if target["boss"] else 0.32)
            event = self._projectile_event(
                self.BUBBLE_CHAIN_DELAY,
                target,
                chain["damage"],
                chain["origin_x"],
                chain["origin_z"],
                1.2,
                0.34 * self._reach_multiplier(),
                hit_speed=2.4,
                source_id="bubble",
            )
            self._spawn_projectile(
                self.BUBBLE_EFFECT,
                chain["origin_x"], chain["origin_y"], chain["origin_z"],
                target_pos.x, target_y, target_pos.z,
                self.BUBBLE_CHAIN_DELAY,
                self.BUBBLE_PROJECTILE_SCALE * self._reach_multiplier(),
                1.0,
                [event],
                arc_height=0.14,
                homing_target=target,
                visual_kind="bubble",
                visual_scale=0.56,
                source_id="bubble",
            )
            chain["origin_x"] = target_pos.x
            chain["origin_y"] = target_y
            chain["origin_z"] = target_pos.z
            chain["origin_target"] = target
            chain["origin_activation_id"] = target.get("activation_id", -1)
            chain["index"] += 1
            chain["timer"] = self.BUBBLE_CHAIN_DELAY
            if chain["index"] < len(targets):
                active_chains.append(chain)
        self.active_bubble_chains = active_chains

    def _fire_tornado(self, player_pos):
        target_rows = HEngine.SelectDensestSurvivorAgents(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            self._weapon_reach(2.6),
            1,
        )
        target = None
        target_position = None
        for _, entity_id, activation_id, x, y, z, _, _ in target_rows:
            target = self._resolve_survivor_target(entity_id, activation_id)
            if target is not None:
                target_position = (x, y, z)
                break
        if target is None:
            self.tornado_timer = 0.12
            return

        target_x, target_y, target_z = target_position
        radius = self._tornado_radius()
        HEngine.VFX.PlayEffectAdvanced(
            self.TORNADO_EFFECT,
            target_x, target_y + 0.08, target_z,
            # MagicTornade is authored as a vertical column. Identity forward
            # keeps it upright while the gameplay zone stays fixed below it.
            0.0, 0.0, -1.0,
            0.26 * self._reach_multiplier(), 1.9,
        )
        self.active_tornado_zones.append({
            "x": target_x,
            "y": target_y,
            "z": target_z,
            "age": 0.0,
            "duration": self._tornado_duration(),
            "tick_timer": 0.0,
            "tick_interval": self._tornado_tick_interval(),
            "tick_index": 0,
            "radius": radius,
            "damage": self._tornado_damage(),
        })
        self.audio.weapon_cast("tornado", player_pos)
        self.tornado_timer = self._tornado_interval()

    def _update_tornado_zones(self, dt):
        active_zones = []
        for zone in self.active_tornado_zones:
            zone["age"] += dt
            if self._has_evolution("tornado", "storybooktempest"):
                candidates = self._weapon_candidates(
                    zone["x"], zone["y"], zone["z"], self._weapon_reach(5.0),
                )
                if candidates:
                    target_pos = candidates[0][1]["transform"].Translation
                    follow = min(1.0, dt * 1.8)
                    zone["x"] += (target_pos.x - zone["x"]) * follow
                    zone["z"] += (target_pos.z - zone["z"]) * follow
                zone["radius"] *= 1.0 + dt * 0.08
            zone["tick_timer"] -= dt
            if zone["tick_timer"] <= 0.0:
                zone["tick_timer"] += zone["tick_interval"]
                # Negative force pulls toward the visual column.  The previous
                # positive value pushed targets outward while the effect looked
                # like suction.  Bosses remain immune to displacement.
                force = -(
                    1.8 + self.tornado_level * 0.18
                    if zone["tick_index"] == 0 else
                    0.18
                )
                for _, monster in self._weapon_candidates(
                        zone["x"], zone["y"], zone["z"], zone["radius"]):
                    self._apply_weapon_damage(
                        monster,
                        zone["damage"],
                        zone["x"],
                        zone["z"],
                        0.0 if monster.get("boss", False) else force,
                        True,
                        "tornado",
                    )
                zone["tick_index"] += 1
            if zone["age"] < zone["duration"]:
                active_zones.append(zone)
            elif self._has_evolution("tornado", "storybooktempest"):
                for index in range(4):
                    angle = math.pi * 0.5 * index
                    self._queue_custom_area(
                        "tornado",
                        zone["x"] + math.cos(angle) * zone["radius"] * 0.7,
                        zone["y"],
                        zone["z"] + math.sin(angle) * zone["radius"] * 0.7,
                        0.08 * index,
                        zone["radius"] * 0.35,
                        zone["damage"] * 1.5,
                        force=0.45,
                    )
        self.active_tornado_zones = active_zones

    def _fire_starfall(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        drop_count = min(3, self._catalog_weapon_stats("starfall")["amount"])
        ordered = sorted(
            candidates,
            key=lambda item: (
                item[1]["boss"],
                item[1]["health"],
                item[1]["max_health"],
                -item[0],
            ),
            reverse=True,
        )
        targets = []
        separation_sq = self._weapon_reach(2.4) ** 2
        for _, candidate in ordered:
            candidate_pos = candidate["transform"].Translation
            if any(
                    (selected["transform"].Translation.x - candidate_pos.x) ** 2
                    + (selected["transform"].Translation.z - candidate_pos.z) ** 2
                    < separation_sq
                    for selected in targets):
                continue
            targets.append(candidate)
            if len(targets) >= drop_count:
                break
        if not targets:
            self.starfall_timer = 0.12
            return

        radius = self._starfall_radius()
        volley_hit_ids = set()
        for target in targets:
            target_pos = target["transform"].Translation
            HEngine.VFX.PlayEffectAdvanced(
                self.STARFALL_EFFECT,
                target_pos.x, target_pos.y + 0.08, target_pos.z,
                0.0, 0.0, -1.0,
                0.15 * self._reach_multiplier(), 1.75,
            )
            self.active_starfall_impacts.append({
                "x": target_pos.x,
                "y": target_pos.y,
                "z": target_pos.z,
                "timer": self.STARFALL_IMPACT_DELAY,
                "radius": radius,
                "damage": self._starfall_damage(),
                "hit_ids": volley_hit_ids,
            })
        self.audio.weapon_cast("starfall", player_pos)
        self.starfall_timer = self._starfall_interval()

    def _update_starfall_impacts(self, dt):
        active_impacts = []
        for impact in self.active_starfall_impacts:
            impact["timer"] -= dt
            if impact["timer"] > 0.0:
                active_impacts.append(impact)
                continue

            for _, monster in self._weapon_candidates(
                    impact["x"], impact["y"], impact["z"], impact["radius"]):
                entity_id = monster["entity_id"]
                if entity_id in impact["hit_ids"]:
                    continue
                impact["hit_ids"].add(entity_id)
                self._apply_weapon_damage(
                    monster,
                    impact["damage"],
                    impact["x"],
                    impact["z"],
                    2.4 + self.starfall_level * 0.18,
                    True,
                    "starfall",
                )
        self.active_starfall_impacts = active_impacts

    def _fire_aura(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            self.aura_timer = 0.10
            return

        candidates.sort(key=lambda item: item[0])
        projectile_count = self._aura_projectile_count()
        for projectile_index in range(projectile_count):
            target = candidates[projectile_index % len(candidates)][1]
            target_pos = target["transform"].Translation
            shoulder_angle = math.pi * 2.0 * projectile_index / projectile_count
            origin_x = player_pos.x + math.cos(shoulder_angle) * 0.24
            origin_z = player_pos.z + math.sin(shoulder_angle) * 0.24
            end_y = target_pos.y + (0.52 if target["boss"] else 0.34)
            distance = max(
                0.001,
                (
                    (target_pos.x - origin_x) ** 2
                    + (target_pos.z - origin_z) ** 2
                ) ** 0.5,
            )
            duration = self._projectile_travel_time(min(0.56, max(0.24, distance / 13.5)))
            event = self._projectile_event(
                duration,
                target,
                self._aura_damage(),
                player_pos.x,
                player_pos.z,
                0.45,
                0.07 * self._reach_multiplier(),
                source_id="aura",
            )
            self._spawn_projectile(
                self.AURA_EFFECT,
                origin_x, player_pos.y + 0.58, origin_z,
                target_pos.x, end_y, target_pos.z,
                duration,
                self.WISP_PROJECTILE_SCALE * self._reach_multiplier(),
                1.0,
                [event],
                arc_height=0.24,
                launch_delay=projectile_index * 0.045,
                homing_target=target,
                source_id="aura",
            )
        self.audio.weapon_cast("aura", player_pos)
        self.aura_timer = self._aura_interval()

    def _fire_dagger(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            self.dagger_timer = 0.08
            return

        primary = min(candidates, key=lambda item: item[0])[1]
        primary_pos = primary["transform"].Translation
        aim_x = primary_pos.x - player_pos.x
        aim_z = primary_pos.z - player_pos.z
        aim_length = max(0.001, (aim_x * aim_x + aim_z * aim_z) ** 0.5)
        aim_x /= aim_length
        aim_z /= aim_length

        projectile_count = self._dagger_projectile_count()
        travel_distance = self._weapon_reach(10.0)
        duration = self._projectile_travel_time(0.62)
        max_hits = 2 if self.dagger_level >= 5 else 1
        projectile_specs = []
        for projectile_index, angle in enumerate(
                self._fan_angles(projectile_count, math.radians(24.0))):
            direction_x, direction_z = self._rotated_direction(
                aim_x,
                aim_z,
                angle,
            )
            lateral_index = projectile_index - (projectile_count - 1) * 0.5
            origin_x = player_pos.x - aim_z * lateral_index * 0.12
            origin_z = player_pos.z + aim_x * lateral_index * 0.12
            projectile_specs.append((origin_x, origin_z, direction_x, direction_z))

        corridor_batches = HEngine.QuerySurvivorAgentCorridors(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            [
                (
                    origin_x,
                    origin_z,
                    direction_x,
                    direction_z,
                    travel_distance,
                    self._weapon_reach(0.34),
                    max_hits,
                )
                for origin_x, origin_z, direction_x, direction_z in projectile_specs
            ],
        )
        for projectile_index, (
                (origin_x, origin_z, direction_x, direction_z),
                hit_rows,
        ) in enumerate(zip(projectile_specs, corridor_batches)):
            corridor_hits = []
            for along, entity_id, activation_id, _, _, _, _ in hit_rows:
                target = self._resolve_survivor_target(entity_id, activation_id)
                if target is not None:
                    corridor_hits.append((along, target))
            events = [
                self._projectile_event(
                    max(0.04, duration * along / travel_distance),
                    target,
                    self._dagger_damage(),
                    player_pos.x,
                    player_pos.z,
                    0.8,
                    0.06 * self._reach_multiplier(),
                    source_id="dagger",
                )
                for along, target in corridor_hits
            ]
            self._spawn_projectile(
                self.DAGGER_EFFECT,
                origin_x, player_pos.y + 0.66, origin_z,
                origin_x + direction_x * travel_distance,
                player_pos.y + 0.66,
                origin_z + direction_z * travel_distance,
                duration,
                self.DAGGER_PROJECTILE_SCALE * self._reach_multiplier(),
                1.0,
                events,
                arc_height=0.05,
                launch_delay=projectile_index * 0.035,
                visual_kind="bolt",
                visual_scale=0.18,
                source_id="dagger",
            )
        self.audio.weapon_cast("dagger", player_pos)
        self.dagger_timer = self._dagger_interval()

    def _fire_starwheel(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x,
            player_pos.y,
            player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            self.starwheel_timer = 0.10
            return

        primary = min(candidates, key=lambda item: item[0])[1]
        primary_pos = primary["transform"].Translation
        aim_x = primary_pos.x - player_pos.x
        aim_z = primary_pos.z - player_pos.z
        aim_length = max(0.001, (aim_x * aim_x + aim_z * aim_z) ** 0.5)
        aim_x /= aim_length
        aim_z /= aim_length

        projectile_count = self._starwheel_projectile_count()
        travel_distance = self._weapon_reach(6.8)
        duration = self._projectile_travel_time(1.15) * self._duration_multiplier()
        spread = math.radians(28.0 if projectile_count > 1 else 0.0)
        sweep_targets = [target for _, target in candidates]
        for projectile_index, angle in enumerate(
                self._fan_angles(projectile_count, spread)):
            direction_x, direction_z = self._rotated_direction(
                aim_x,
                aim_z,
                angle,
            )
            self._spawn_projectile(
                self.STARWHEEL_EFFECT,
                player_pos.x, player_pos.y + 0.54, player_pos.z,
                player_pos.x + direction_x * travel_distance,
                player_pos.y + 0.54,
                player_pos.z + direction_z * travel_distance,
                duration,
                self.STARWHEEL_PROJECTILE_SCALE * self._reach_multiplier(),
                0.85,
                [],
                trajectory="boomerang",
                arc_height=0.68,
                launch_delay=projectile_index * 0.07,
                return_to_player=True,
                return_y_offset=0.54,
                return_curve=self._weapon_reach(1.15),
                return_curve_sign=(-1.0 if angle < 0.0 else 1.0),
                sweep_targets=sweep_targets,
                sweep_damage=self._starwheel_damage(),
                sweep_radius=self._weapon_reach(0.62),
                sweep_force=0.7,
                sweep_hit_scale=0.11 * self._reach_multiplier(),
                sweep_max_hits=8,
                visual_kind="wheel",
                visual_scale=0.50,
                source_id="starwheel",
            )
        self.audio.weapon_cast("starwheel", player_pos)
        self.starwheel_timer = self._starwheel_interval()

    def _fire_petalstorm(self, player_pos):
        HEngine.VFX.PlayEffectAdvanced(
            self.PETALSTORM_EFFECT,
            player_pos.x, player_pos.y + 0.08, player_pos.z,
            0.0, 0.0, -1.0,
            0.28 * self._reach_multiplier(), 2.2,
        )
        petal_stats = self._catalog_weapon_stats("petalstorm")
        projectile_count = min(24, petal_stats["amount"])
        travel_distance = self._weapon_reach(7.4)
        duration = self._projectile_travel_time(0.92)
        candidates = self._weapon_candidates(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        sweep_targets = [target for _, target in candidates]
        for projectile_index in range(projectile_count):
            angle = math.pi * 2.0 * projectile_index / projectile_count
            direction_x = math.sin(angle)
            direction_z = math.cos(angle)
            self._spawn_projectile(
                self.PETALSTORM_EFFECT,
                player_pos.x, player_pos.y + 0.50, player_pos.z,
                player_pos.x + direction_x * travel_distance,
                player_pos.y + 0.50,
                player_pos.z + direction_z * travel_distance,
                duration,
                0.42 * self._reach_multiplier(), 1.0,
                [],
                arc_height=0.16,
                launch_delay=(projectile_index % 3) * 0.018,
                sweep_targets=sweep_targets,
                sweep_damage=petal_stats["damage"],
                sweep_radius=self._weapon_reach(0.38),
                sweep_force=0.35,
                sweep_hit_scale=0.06 * self._reach_multiplier(),
                sweep_max_hits=2,
                visual_kind="petal",
                visual_scale=0.48,
                source_id="petalstorm",
            )
        self.audio.weapon_cast("dagger", player_pos)
        if self._has_evolution("petalstorm", "galaxygarden"):
            bloom_radius = self._weapon_reach(6.0)
            for index in range(5):
                angle = math.pi * 2.0 * index / 5.0
                self._queue_custom_area(
                    "petalstorm",
                    player_pos.x + math.cos(angle) * bloom_radius,
                    player_pos.y,
                    player_pos.z + math.sin(angle) * bloom_radius,
                    1.1,
                    self._weapon_reach(1.1),
                    self._weapon_damage(32.0),
                    force=-0.35,
                )
        self.petalstorm_timer = petal_stats["cooldown"]

    def _fire_comet(self, player_pos):
        candidates = self._weapon_candidates(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            self.comet_timer = 0.08
            return
        candidates.sort(key=lambda item: item[0])
        comet_stats = self._catalog_weapon_stats("comet")
        projectile_count = min(12, comet_stats["amount"])
        for projectile_index in range(projectile_count):
            target = candidates[projectile_index % len(candidates)][1]
            target_pos = target["transform"].Translation
            angle = math.pi * 2.0 * projectile_index / projectile_count
            origin_x = player_pos.x + math.sin(angle) * 0.30
            origin_z = player_pos.z + math.cos(angle) * 0.30
            distance = max(0.01, ((target_pos.x-origin_x)**2 + (target_pos.z-origin_z)**2)**0.5)
            duration = self._projectile_travel_time(min(0.68, max(0.22, distance / 15.0)))
            event = self._projectile_event(
                duration, target,
                comet_stats["damage"],
                player_pos.x, player_pos.z, 0.65,
                0.07 * self._reach_multiplier(),
                source_id="comet",
            )
            self._spawn_projectile(
                self.COMET_EFFECT,
                origin_x, player_pos.y + 0.62, origin_z,
                target_pos.x, target_pos.y + (0.55 if target["boss"] else 0.34), target_pos.z,
                duration, 0.46 * self._reach_multiplier(), 1.0,
                [event],
                arc_height=0.34,
                launch_delay=projectile_index * 0.025,
                homing_target=target,
                visual_kind="comet",
                visual_scale=0.46,
                source_id="comet",
            )
        self.audio.weapon_cast("aura", player_pos)
        self.comet_timer = comet_stats["cooldown"]

    def _catalog_weapon_stats(self, weapon_id):
        definition = WEAPON_DEFS[weapon_id]
        level = max(1, self._weapon_level(weapon_id))
        damage_multiplier = 1.0
        cooldown_multiplier = 1.0
        amount_add = 0
        pierce_add = 0
        bounce_add = 0
        chain_add = 0
        area_add = 0.0
        duration_add = 0.0
        for step in definition["levelPlan"]:
            if step["level"] > level:
                break
            damage_multiplier += step.get("damageMultiplierAdd", 0.0)
            cooldown_multiplier += step.get("cooldownMultiplierAdd", 0.0)
            amount_add += step.get("amountAdd", 0)
            pierce_add += step.get("pierceAdd", 0)
            bounce_add += step.get("bounceAdd", 0)
            chain_add += step.get("chainAdd", 0)
            area_add += step.get("areaAdd", 0.0)
            duration_add += step.get("durationAdd", 0.0)
        friendship_bonus = (
            1
            if getattr(self, "trinket_state", {}).get("friendshipWeapon")
            == weapon_id
            else 0
        )
        bBloomBattery = (
            "bloom_battery" in getattr(self, "trinket_slots", ())
            and bool(set(definition.get("tags", ())) & {"zone", "tick"})
        )
        return {
            "damage": self._weapon_damage(
                definition["baseDamage"] * damage_multiplier,
            ),
            "cooldown": self._weapon_cooldown(
                definition["cooldown"] * max(0.55, cooldown_multiplier),
            ),
            "amount": min(
                24,
                definition["amount"] + amount_add + friendship_bonus
                + self._projectile_bonus(),
            ),
            "pierce": definition["pierce"] + pierce_add,
            "bounce": definition["bounce"] + bounce_add,
            "chain": chain_add,
            "area": self._weapon_reach(
                definition["area"] + area_add,
            ) * self._trinket_area_multiplier(weapon_id),
            "duration": (
                definition["duration"] + duration_add
            ) * self._duration_multiplier() * (0.90 if bBloomBattery else 1.0),
            "speed": definition["speed"] * self._projectile_speed_multiplier(),
        }

    def _record_weapon_cast(self, weapon_id, projectile_count=0):
        telemetry = self.weapon_telemetry[weapon_id]
        telemetry["casts"] += 1
        telemetry["projectiles"] += max(0, int(projectile_count))
        if self.quest_tracker is not None:
            self.quest_tracker.record("casts", 1, {"weapon": weapon_id})

    def _queue_custom_area(
            self,
            weapon_id,
            x,
            y,
            z,
            delay,
            radius,
            initial_damage,
            tick_damage=0.0,
            duration=0.0,
            tick_interval=0.5,
            force=0.4,
            bFollowPlayer=False,
            target_limit=0,
            visual_kind=None,
            visual_count=0):
        definition = WEAPON_DEFS.get(weapon_id, {})
        if (
                "bloom_battery" in getattr(self, "trinket_slots", ())
                and set(definition.get("tags", ())) & {"zone", "tick"}):
            tick_interval *= 0.82
            duration *= 0.90
        visuals = []
        for _ in range(visual_count):
            visual = self._acquire_projectile_visual(visual_kind)
            if visual is not None:
                visuals.append(visual)
        self.active_custom_areas.append({
            "weapon_id": weapon_id,
            "x": x,
            "y": y,
            "z": z,
            "delay": max(0.0, delay),
            "radius": max(0.1, radius),
            "initial_damage": max(0.0, initial_damage),
            "tick_damage": max(0.0, tick_damage),
            "duration": max(0.0, duration),
            "age": 0.0,
            "tick_timer": 0.0,
            "tick_interval": max(0.08, tick_interval),
            "force": force,
            "bActivated": False,
            "bFollowPlayer": bFollowPlayer,
            "target_limit": max(0, int(target_limit)),
            "target_cooldowns": {},
            "visual_kind": visual_kind,
            "visuals": visuals,
        })

    def _release_custom_area_visuals(self, area):
        visual_kind = area.get("visual_kind")
        for entity in area.get("visuals", ()):
            if visual_kind not in self.projectile_visual_pool:
                continue
            transform = entity.GetComponent("Transform")
            transform.Translation = HEngine.vec3(0.0, -100.0, 0.0)
            transform.Scale = self.HIDDEN_SCALE
            self.projectile_visual_pool[visual_kind].append(entity)
        area["visuals"] = []

    def _update_custom_areas(self, dt):
        active = []
        player_pos = self.player.GetComponent("Transform").Translation
        for area in self.active_custom_areas:
            area["delay"] -= dt
            if area["delay"] > 0.0:
                active.append(area)
                continue
            if area["bFollowPlayer"]:
                area["x"] = player_pos.x
                area["y"] = player_pos.y
                area["z"] = player_pos.z
            area["age"] += dt
            cooldowns = area["target_cooldowns"]
            for target_id in tuple(cooldowns):
                cooldowns[target_id] -= dt
                if cooldowns[target_id] <= 0.0:
                    del cooldowns[target_id]

            if not area["bActivated"]:
                area["bActivated"] = True
                area["tick_timer"] = 0.0

            area["tick_timer"] -= dt
            if area["tick_timer"] <= 0.0:
                area["tick_timer"] += area["tick_interval"]
                damage = (
                    area["initial_damage"]
                    if area["age"] <= dt + 0.0001 else
                    area["tick_damage"]
                )
                if damage > 0.0:
                    candidates = self._weapon_candidates(
                        area["x"], area["y"], area["z"], area["radius"],
                    )
                    if area["target_limit"] > 0:
                        candidates = candidates[:area["target_limit"]]
                    for _, monster in candidates:
                        target_key = (
                            monster["entity_id"],
                            monster.get("activation_id", -1),
                        )
                        if target_key in cooldowns:
                            continue
                        cooldowns[target_key] = area["tick_interval"] * 0.90
                        self._apply_weapon_damage(
                            monster,
                            damage,
                            area["x"],
                            area["z"],
                            area["force"],
                            True,
                            area["weapon_id"],
                        )

            visuals = area.get("visuals", ())
            visual_count = max(1, len(visuals))
            for index, entity in enumerate(visuals):
                angle = area["age"] * 2.4 + math.pi * 2.0 * index / visual_count
                orbit_radius = max(0.8, min(2.4, area["radius"] * 0.38))
                transform = entity.GetComponent("Transform")
                transform.Translation = HEngine.vec3(
                    area["x"] + math.cos(angle) * orbit_radius,
                    area["y"] + 0.58 + math.sin(area["age"] * 3.0 + index) * 0.12,
                    area["z"] + math.sin(angle) * orbit_radius,
                )
                scale = 0.30 if area["visual_kind"] == "frost" else 0.38
                transform.Scale = HEngine.vec3(scale, scale, scale)
                transform.Rotation = HEngine.vec3(0.0, -angle, area["age"] * 1.8)

            if area["age"] < area["duration"] or area["duration"] >= 900.0:
                active.append(area)
            else:
                self._release_custom_area_visuals(area)
        self.active_custom_areas = active

    def _update_custom_beams(self, dt):
        active = []
        for beam in self.active_custom_beams:
            beam["delay"] -= dt
            if beam["delay"] > 0.0:
                active.append(beam)
                continue
            definition = WEAPON_DEFS[beam["weapon_id"]]
            HEngine.VFX.PlayEffectAdvanced(
                definition["bodyVfx"],
                beam["origin_x"], beam["y"], beam["origin_z"],
                beam["direction_x"], 0.0, beam["direction_z"],
                0.48 * self._reach_multiplier(), 1.0,
            )
            for entity_id, activation_id in beam["targets"]:
                target = self._resolve_survivor_target(entity_id, activation_id)
                if target is not None:
                    self._apply_weapon_damage(
                        target,
                        beam["damage"],
                        beam["origin_x"],
                        beam["origin_z"],
                        1.0,
                        True,
                        beam["weapon_id"],
                    )
        self.active_custom_beams = active

    def _fire_fan_catalog_weapon(
            self,
            weapon_id,
            player_pos,
            visual_kind,
            spread_degrees,
            travel_distance):
        stats = self._catalog_weapon_stats(weapon_id)
        candidates = self._weapon_candidates(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            setattr(self, weapon_id + "_timer", 0.08)
            return
        target = candidates[0][1]
        target_pos = target["transform"].Translation
        aim_x = target_pos.x - player_pos.x
        aim_z = target_pos.z - player_pos.z
        aim_length = max(0.001, (aim_x * aim_x + aim_z * aim_z) ** 0.5)
        aim_x /= aim_length
        aim_z /= aim_length
        specs = []
        for angle in self._fan_angles(stats["amount"], math.radians(spread_degrees)):
            direction_x, direction_z = self._rotated_direction(aim_x, aim_z, angle)
            specs.append((direction_x, direction_z))
        corridor_batches = HEngine.QuerySurvivorAgentCorridors(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            [(
                player_pos.x,
                player_pos.z,
                direction_x,
                direction_z,
                self._weapon_reach(travel_distance),
                max(0.24, stats["area"]),
                max(1, stats["pierce"] + 1),
            ) for direction_x, direction_z in specs],
        )
        duration = self._projectile_travel_time(
            self._weapon_reach(travel_distance) / max(1.0, stats["speed"]),
        )
        for projectile_index, ((direction_x, direction_z), rows) in enumerate(
                zip(specs, corridor_batches)):
            events = []
            for along, entity_id, activation_id, _, _, _, _ in rows:
                hit_target = self._resolve_survivor_target(entity_id, activation_id)
                if hit_target is not None:
                    events.append(self._projectile_event(
                        max(0.03, duration * along / self._weapon_reach(travel_distance)),
                        hit_target,
                        stats["damage"],
                        player_pos.x,
                        player_pos.z,
                        WEAPON_DEFS[weapon_id]["knockback"],
                        0.07,
                        WEAPON_DEFS[weapon_id]["impactVfx"],
                        3.2,
                        weapon_id,
                    ))
            self._spawn_projectile(
                WEAPON_DEFS[weapon_id]["bodyVfx"],
                player_pos.x, player_pos.y + 0.62, player_pos.z,
                player_pos.x + direction_x * self._weapon_reach(travel_distance),
                player_pos.y + 0.62,
                player_pos.z + direction_z * self._weapon_reach(travel_distance),
                max(0.18, duration),
                0.36 * self._reach_multiplier(),
                1.0,
                events,
                launch_delay=projectile_index * 0.025,
                visual_kind=visual_kind,
                visual_scale=0.42,
            )
        self._record_weapon_cast(weapon_id, stats["amount"])
        self.audio.weapon_cast(weapon_id, player_pos)
        setattr(self, weapon_id + "_timer", stats["cooldown"])

    def _fire_honeyneedle(self, player_pos):
        self._fire_fan_catalog_weapon("honeyneedle", player_pos, "needle", 22.0, 12.0)

    def _fire_sporecap(self, player_pos):
        stats = self._catalog_weapon_stats("sporecap")
        targets = HEngine.SelectDensestSurvivorAgents(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            stats["area"],
            1,
        )
        if not targets:
            self.sporecap_timer = 0.10
            return
        _, _, _, x, y, z, _, _ = targets[0]
        travel_time = 0.58
        self._spawn_projectile(
            WEAPON_DEFS["sporecap"]["bodyVfx"],
            player_pos.x, player_pos.y + 0.72, player_pos.z,
            x, y + 0.18, z,
            travel_time, 0.42, 1.0, [],
            arc_height=1.8,
            visual_kind="spore",
            visual_scale=0.48,
        )
        self._queue_custom_area(
            "sporecap", x, y, z, travel_time, stats["area"], stats["damage"],
            self._weapon_damage(4.0), stats["duration"], 0.5, 0.25,
        )
        self._record_weapon_cast("sporecap", 1)
        self.audio.weapon_cast("sporecap", player_pos)
        self.sporecap_timer = stats["cooldown"]

    def _fire_phantombell(self, player_pos):
        stats = self._catalog_weapon_stats("phantombell")
        echo_damage = 0.75 if self.phantombell_level >= 5 else 0.55
        echo_count = 2 if self.phantombell_level >= 7 else 1
        self._queue_custom_area(
            "phantombell", player_pos.x, player_pos.y, player_pos.z,
            0.0, stats["area"], stats["damage"], force=0.35,
            visual_kind="bell", visual_count=1,
        )
        for echo_index in range(echo_count):
            self._queue_custom_area(
                "phantombell", player_pos.x, player_pos.y, player_pos.z,
                0.65 * (echo_index + 1), stats["area"],
                stats["damage"] * echo_damage, force=0.18,
            )
        self._record_weapon_cast("phantombell")
        self.audio.weapon_cast("phantombell", player_pos)
        self.phantombell_timer = stats["cooldown"]

    def _fire_returning_catalog_weapon(
            self,
            weapon_id,
            player_pos,
            visual_kind,
            travel_distance,
            radius,
            force):
        stats = self._catalog_weapon_stats(weapon_id)
        candidates = self._weapon_candidates(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
        )
        if not candidates:
            setattr(self, weapon_id + "_timer", 0.10)
            return
        target_pos = candidates[0][1]["transform"].Translation
        aim_x = target_pos.x - player_pos.x
        aim_z = target_pos.z - player_pos.z
        aim_length = max(0.001, (aim_x * aim_x + aim_z * aim_z) ** 0.5)
        aim_x /= aim_length
        aim_z /= aim_length
        amount = min(3, stats["amount"])
        for index, angle in enumerate(self._fan_angles(amount, math.radians(22.0))):
            direction_x, direction_z = self._rotated_direction(aim_x, aim_z, angle)
            self._spawn_projectile(
                WEAPON_DEFS[weapon_id]["bodyVfx"],
                player_pos.x, player_pos.y + 0.55, player_pos.z,
                player_pos.x + direction_x * self._weapon_reach(travel_distance),
                player_pos.y + 0.38,
                player_pos.z + direction_z * self._weapon_reach(travel_distance),
                1.15 * self._duration_multiplier(),
                0.45, 1.0, [],
                trajectory="boomerang",
                arc_height=0.55,
                launch_delay=index * 0.06,
                return_to_player=True,
                return_y_offset=0.55,
                return_curve=self._weapon_reach(0.8),
                sweep_targets=[candidate for _, candidate in candidates],
                sweep_damage=stats["damage"],
                sweep_radius=self._weapon_reach(radius),
                sweep_force=force,
                sweep_hit_scale=0.10,
                sweep_max_hits=max(1, stats["pierce"]),
                visual_kind=visual_kind,
                visual_scale=0.50,
                source_id=weapon_id,
            )
        self._record_weapon_cast(weapon_id, amount)
        self.audio.weapon_cast(weapon_id, player_pos)
        setattr(self, weapon_id + "_timer", stats["cooldown"])

    def _fire_coralanchor(self, player_pos):
        self._fire_returning_catalog_weapon(
            "coralanchor", player_pos, "anchor", 7.0, 0.75, 1.3,
        )
        if self._has_evolution("coralanchor", "tidalfortress"):
            self.character_hook_state["tidalFortress"] = min(
                self.max_health * 0.30,
                self.character_hook_state.get("tidalFortress", 0.0) + 24.0,
            )

    def _fire_prismorbit(self, player_pos):
        stats = self._catalog_weapon_stats("prismorbit")
        self._queue_custom_area(
            "prismorbit", player_pos.x, player_pos.y, player_pos.z,
            0.0, self._weapon_reach(6.0), stats["damage"], stats["damage"],
            stats["duration"], 0.20, 0.05, True, stats["amount"],
            "prism", stats["amount"],
        )
        self._record_weapon_cast("prismorbit")
        self.audio.weapon_cast("prismorbit", player_pos)
        self.prismorbit_timer = stats["cooldown"]

    def _fire_acornmortar(self, player_pos):
        stats = self._catalog_weapon_stats("acornmortar")
        targets = HEngine.SelectDensestSurvivorAgents(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            stats["area"], 1,
        )
        if not targets:
            self.acornmortar_timer = 0.10
            return
        _, _, _, x, y, z, _, _ = targets[0]
        travel_time = 0.62
        self._spawn_projectile(
            WEAPON_DEFS["acornmortar"]["bodyVfx"],
            player_pos.x, player_pos.y + 0.70, player_pos.z,
            x, y + 0.10, z, travel_time, 0.44, 1.0, [],
            arc_height=2.0, visual_kind="acorn", visual_scale=0.52,
        )
        self._queue_custom_area(
            "acornmortar", x, y, z, travel_time, stats["area"], stats["damage"],
            force=0.8,
        )
        child_count = 7 if self.acornmortar_level >= 10 else 3 + (1 if self.acornmortar_level >= 3 else 0)
        for index in range(child_count):
            angle = math.pi * 2.0 * index / child_count
            self._queue_custom_area(
                "acornmortar",
                x + math.cos(angle) * stats["area"] * 0.72,
                y,
                z + math.sin(angle) * stats["area"] * 0.72,
                travel_time + 0.14,
                stats["area"] * 0.36,
                stats["damage"] / 3.0,
                force=0.35,
            )
        self._record_weapon_cast("acornmortar", 1 + child_count)
        self.audio.weapon_cast("acornmortar", player_pos)
        self.acornmortar_timer = stats["cooldown"]

    def _fire_frostorb(self, player_pos):
        if any(
                area["weapon_id"] == "frostorb"
                for area in self.active_custom_areas):
            self.frostorb_timer = 0.50
            return
        stats = self._catalog_weapon_stats("frostorb")
        self._queue_custom_area(
            "frostorb", player_pos.x, player_pos.y, player_pos.z,
            0.0, self._weapon_reach(2.2), stats["damage"], stats["damage"],
            999.0, 0.55, 0.10, True, 0,
            "frost", stats["amount"],
        )
        self._record_weapon_cast("frostorb", stats["amount"])
        self.audio.weapon_cast("frostorb", player_pos)
        self.frostorb_timer = 0.50

    def _fire_gravityyoyo(self, player_pos):
        self._fire_returning_catalog_weapon(
            "gravityyoyo", player_pos, "yoyo", 8.0, 0.58, 0.45,
        )

    def _fire_rainbowrail(self, player_pos):
        stats = self._catalog_weapon_stats("rainbowrail")
        corridor_specs = []
        corridor_count = 16
        distance = self._weapon_reach(12.0)
        for index in range(corridor_count):
            angle = math.pi * 2.0 * index / corridor_count
            corridor_specs.append((
                player_pos.x,
                player_pos.z,
                math.sin(angle),
                math.cos(angle),
                distance,
                stats["area"],
                64,
            ))
        batches = HEngine.QuerySurvivorAgentCorridors(
            player_pos.x, player_pos.y, player_pos.z,
            self._weapon_reach(self.SCREEN_ATTACK_RANGE),
            self.WEAPON_VERTICAL_RANGE,
            corridor_specs,
        )
        if not batches or max(len(rows) for rows in batches) == 0:
            self.rainbowrail_timer = 0.10
            return
        best_index = max(range(len(batches)), key=lambda index: len(batches[index]))
        spec = corridor_specs[best_index]
        targets = tuple((row[1], row[2]) for row in batches[best_index])
        self.active_custom_beams.append({
            "weapon_id": "rainbowrail",
            "delay": 0.55,
            "origin_x": player_pos.x,
            "origin_z": player_pos.z,
            "y": player_pos.y + 0.52,
            "direction_x": spec[2],
            "direction_z": spec[3],
            "targets": targets,
            "damage": stats["damage"],
        })
        self._record_weapon_cast("rainbowrail")
        self.audio.weapon_cast("rainbowrail", player_pos)
        self.rainbowrail_timer = stats["cooldown"]

    def _apply_weapon_damage(
            self,
            target,
            damage,
            origin_x,
            origin_z,
            force,
            bCanCritical,
            source_id=""):
        if target["dead"]:
            return
        if target.get("domain_vulnerability_remaining", 0.0) > 0.0:
            damage *= 1.0 + target.get("domain_vulnerability", 0.08)
        damage *= self._trinket_damage_multiplier(source_id, target)
        critical = bCanCritical and self._random_uniform(0.0, 1.0) < self.crit_chance
        if critical:
            damage *= self.crit_multiplier
            self.banner_timer = 0.32
            self.banner_key = "critical_banner"
            if self.document_id:
                self._set_hud_text("banner", self._text(self.banner_key))

        applied_damage = max(0.0, min(float(damage), target["health"]))
        telemetry = self.weapon_telemetry.get(source_id)
        if telemetry is not None:
            telemetry["damage"] += applied_damage
            telemetry["hits"] += 1
            if critical:
                telemetry["criticalHits"] += 1
        if self.quest_tracker is not None and source_id:
            base_source = source_id.split(":", 1)[0]
            tags = self.weapon_tag_cache.get(base_source, frozenset())
            self.quest_tracker.record(
                "hits", 1, {"weapon": base_source, "tags": tuple(tags)},
            )
            self.quest_tracker.record(
                "damage", applied_damage,
                {"weapon": base_source, "tags": tuple(tags), "path": "return" if "return" in tags else "outbound"},
            )
            if "projectile" in tags:
                self.quest_tracker.record("projectile_hits", 1, {"weapon": base_source})
            if WEAPON_DEFS.get(base_source, {}).get("pierce", 0) > 0:
                self.quest_tracker.record("pierce_hits", 1, {"weapon": base_source})
            if base_source == "bubble":
                self.quest_tracker.record("bounce_hits", 1, {"weapon": base_source})
            if force > 0.0 and base_source in ("coralanchor", "gravityyoyo"):
                self.quest_tracker.record("enemies_moved", 1, {"weapon": base_source})
            if critical:
                self.quest_tracker.record("critical_hits", 1, {"weapon": base_source})
            target["last_damage_tags"] = tuple(tags)
            target["last_damage_weapon"] = base_source

        target_pos = target["transform"].Translation
        direction_x = target_pos.x - origin_x
        direction_z = target_pos.z - origin_z
        direction_length = max(
            0.001,
            (direction_x * direction_x + direction_z * direction_z) ** 0.5,
        )
        target["health"] = HEngine.ApplySurvivorAgentHit(
            target["entity"],
            damage,
            direction_x / direction_length * force,
            direction_z / direction_length * force,
        )
        self._on_weapon_hit_trinkets(
            source_id,
            target,
            applied_damage,
            critical,
        )
        base_source = source_id.split(":", 1)[0]
        status_to_apply = None
        status_magnitude = 0.0
        status_duration = 0.0
        if (
                base_source == "frostorb"
                and self._random_uniform(0.0, 1.0)
                < (0.25 if self.frostorb_level >= 5 else 0.15)):
            status_to_apply = "freeze"
            status_magnitude = 1.0
            status_duration = (1.1 if self.frostorb_level >= 5 else 0.8)
        elif base_source == "honeyneedle" and self.honeyneedle_level >= 5:
            status_to_apply = "slow"
            status_magnitude = 0.20
            status_duration = 1.4
        if status_to_apply is not None:
            apply_status = getattr(HEngine, "ApplySurvivorAgentStatus", None)
            if apply_status is not None:
                accepted, applied_duration, _ = apply_status(
                    target["entity"],
                    status_to_apply,
                    status_magnitude,
                    status_duration * self.status_multiplier,
                    target.get("activation_id", 0),
                )
                if accepted and applied_duration > 0.0 and self.quest_tracker is not None:
                    self.quest_tracker.record(
                        "status_applied", 1, {"status": status_to_apply},
                    )
        if (
                source_id == "comet"
                and self._has_evolution("comet", "supernovachoir")):
            target_pos = target["transform"].Translation
            nearby = [
                monster for _, monster in self._weapon_candidates(
                    target_pos.x, target_pos.y, target_pos.z, 2.5,
                )
                if monster is not target
            ][:4]
            for monster in nearby:
                self._apply_weapon_damage(
                    monster,
                    applied_damage * 0.28,
                    target_pos.x,
                    target_pos.z,
                    0.12,
                    False,
                    "comet:evolved",
                )
        if (
                source_id == "dagger"
                and self._has_evolution("dagger", "nebulanetwork")):
            target_pos = target["transform"].Translation
            previous = getattr(self, "_nebula_last_hit", None)
            if previous is not None:
                midpoint_x = (previous[0] + target_pos.x) * 0.5
                midpoint_z = (previous[1] + target_pos.z) * 0.5
                self._queue_custom_area(
                    "dagger", midpoint_x, target_pos.y, midpoint_z,
                    0.0, self._weapon_reach(0.65),
                    applied_damage * 0.35, duration=0.8, tick_interval=0.4,
                )
            self._nebula_last_hit = (target_pos.x, target_pos.z)
        if (
                source_id == "honeyneedle"
                and self._has_evolution("honeyneedle", "royalbeehive")):
            target["hive_edges"] = target.get("hive_edges", 0) + 1
            if target["hive_edges"] >= 6:
                target["hive_edges"] = 0
                target_pos = target["transform"].Translation
                self._queue_custom_area(
                    "honeyneedle", target_pos.x, target_pos.y, target_pos.z,
                    0.0, self._weapon_reach(2.0), applied_damage * 1.8,
                    force=0.35,
                )
        if (
                base_source == "phantombell"
                and critical
                and self._has_evolution("phantombell", "midnightencore")):
            notes = self.character_hook_state.get("encoreNotes", 0) + 1
            if notes >= 8:
                notes = 0
                player_pos = self.player.GetComponent("Transform").Translation
                self._queue_custom_area(
                    "phantombell", player_pos.x, player_pos.y, player_pos.z,
                    0.0, self._weapon_reach(4.2), self._weapon_damage(52.0),
                    force=0.45,
                )
            self.character_hook_state["encoreNotes"] = notes
        if (
                base_source == "prismorbit"
                and self._has_evolution("prismorbit", "friendshipspectrum")):
            statuses = ("slow", "poison")
            status_id = statuses[
                int(self._random_uniform(0.0, float(len(statuses)))) % len(statuses)
            ]
            apply_status = getattr(HEngine, "ApplySurvivorAgentStatus", None)
            if apply_status is not None:
                accepted, applied_duration, _ = apply_status(
                    target["entity"], status_id, 0.18, 1.2,
                    target.get("activation_id", 0),
                )
                if accepted and applied_duration > 0.0 and self.quest_tracker is not None:
                    self.quest_tracker.record(
                        "status_applied", 1, {"status": status_id},
                    )
        if source_id == "honeyneedle":
            self._dispatch_combat_hook(
                "hit", {"target": target, "damage": applied_damage},
            )
        if source_id in ("sporecap", "myceliumcarnival"):
            target["poison_remaining_damage"] = max(
                target.get("poison_remaining_damage", 0.0),
                self._weapon_damage(4.0) * 6.0,
            )
            target.setdefault("poison_generation", 0)
        if target["health"] <= 0.0:
            if telemetry is not None:
                telemetry["kills"] += 1
            if critical:
                self._on_critical_kill_trinkets()
                if self.quest_tracker is not None:
                    self.quest_tracker.record("critical_kills", 1)
            self._dispatch_combat_hook(
                "kill",
                {
                    "target": target,
                    "poisonRemaining": target.get("poison_remaining_damage", 0.0),
                    "generation": target.get("poison_generation", 0),
                },
            )
            self._kill_monster(target)
        else:
            self.audio.post("monster_hit", target_pos)

    def _thunder_damage(self):
        return self._catalog_weapon_stats("thunder")["damage"]

    def _thunder_interval(self):
        return self._catalog_weapon_stats("thunder")["cooldown"]

    def _thunder_target_count(self):
        stats = self._catalog_weapon_stats("thunder")
        return min(10, stats["amount"] + stats["chain"])

    def _ring_damage(self):
        return self._catalog_weapon_stats("ring")["damage"]

    def _ring_radius(self):
        return self._catalog_weapon_stats("ring")["area"]

    def _ring_interval(self):
        return self._catalog_weapon_stats("ring")["cooldown"]

    def _fireball_damage(self):
        return self._catalog_weapon_stats("fireball")["damage"]

    def _fireball_interval(self):
        return self._catalog_weapon_stats("fireball")["cooldown"]

    def _fireball_target_count(self):
        return self._catalog_weapon_stats("fireball")["amount"]

    def _moonblade_damage(self):
        return self._catalog_weapon_stats("moonblade")["damage"]

    def _moonblade_interval(self):
        return self._catalog_weapon_stats("moonblade")["cooldown"]

    def _bubble_damage(self):
        return self._catalog_weapon_stats("bubble")["damage"]

    def _bubble_interval(self):
        return self._catalog_weapon_stats("bubble")["cooldown"]

    def _tornado_damage(self):
        return self._catalog_weapon_stats("tornado")["damage"]

    def _tornado_radius(self):
        return self._catalog_weapon_stats("tornado")["area"]

    def _tornado_duration(self):
        return self._catalog_weapon_stats("tornado")["duration"]

    def _tornado_tick_interval(self):
        interval = max(0.30, WEAPON_DEFS["tornado"]["hitboxDelay"])
        return interval * (
            0.82 if "bloom_battery" in self.trinket_slots else 1.0
        )

    def _tornado_interval(self):
        return self._catalog_weapon_stats("tornado")["cooldown"]

    def _starfall_damage(self):
        return self._catalog_weapon_stats("starfall")["damage"]

    def _starfall_radius(self):
        return self._catalog_weapon_stats("starfall")["area"]

    def _starfall_interval(self):
        return self._catalog_weapon_stats("starfall")["cooldown"]

    def _aura_damage(self):
        return self._catalog_weapon_stats("aura")["damage"]

    def _aura_projectile_count(self):
        return self._catalog_weapon_stats("aura")["amount"]

    def _aura_interval(self):
        return self._catalog_weapon_stats("aura")["cooldown"]

    def _dagger_damage(self):
        return self._catalog_weapon_stats("dagger")["damage"]

    def _dagger_projectile_count(self):
        return self._catalog_weapon_stats("dagger")["amount"]

    def _dagger_interval(self):
        return self._catalog_weapon_stats("dagger")["cooldown"]

    def _starwheel_damage(self):
        return self._catalog_weapon_stats("starwheel")["damage"]

    def _starwheel_projectile_count(self):
        return self._catalog_weapon_stats("starwheel")["amount"]

    def _starwheel_interval(self):
        return self._catalog_weapon_stats("starwheel")["cooldown"]

    def _weapon_damage(self, base_damage):
        azura_bonus = 1.0 + getattr(
            self,
            "character_hook_state",
            {},
        ).get("azuraStacks", 0) * 0.04
        return base_damage * (1.0 + self._tome_level("might") * 0.08) * self.character_damage_multiplier * azura_bonus * getattr(self, "weapon_proc_multiplier", 1.0)

    def _weapon_cooldown(self, base_cooldown):
        return base_cooldown * max(0.45, 1.0 - self._tome_level("haste") * 0.05) * self.character_cooldown_multiplier

    def _reach_multiplier(self):
        return (1.0 + self._tome_level("reach") * 0.07) * self.character_reach_multiplier

    def _projectile_bonus(self):
        quantity_level = self._tome_level("quantity")
        return min(3, (quantity_level + 1) // 2) + self.character_projectile_bonus

    def _projectile_speed_multiplier(self):
        return (1.0 + self._tome_level("velocity") * 0.12) * self.character_projectile_speed_multiplier

    def _projectile_travel_time(self, base_duration):
        return base_duration / self._projectile_speed_multiplier()

    def _duration_multiplier(self):
        return (
            1.0 + self._tome_level("duration") * 0.12
        ) * getattr(self, "character_duration_multiplier", 1.0)

    def _weapon_reach(self, base_reach):
        return base_reach * self._reach_multiplier()
