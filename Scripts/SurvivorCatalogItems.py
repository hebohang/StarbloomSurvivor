"""Weapon, evolution, Tome, and Trinket catalogs."""

from SurvivorRuntimeAssets import asset_path


def _level_plan(level3, level5, level7, level10, damage_step=0.12, haste_step=0.04):
    return (
        {"level": 1, "identity": True},
        {"level": 2, "damageMultiplierAdd": damage_step},
        dict({"level": 3}, **level3),
        {"level": 4, "cooldownMultiplierAdd": -haste_step},
        dict({"level": 5}, **level5),
        {"level": 6, "damageMultiplierAdd": damage_step},
        dict({"level": 7}, **level7),
        {"level": 8, "cooldownMultiplierAdd": -haste_step},
        {"level": 9, "damageMultiplierAdd": damage_step * 1.5},
        dict({"level": 10}, **level10),
    )


def _weapon(
        weapon_id,
        zh_name,
        en_name,
        behavior,
        tags,
        base_damage,
        cooldown,
        area,
        speed,
        duration,
        amount,
        pierce,
        bounce,
        knockback,
        hitbox_delay,
        pool_limit,
        visual_limit,
        bHasProjectilePrefab,
        unlock_id,
        evolution_id,
        level_plan,
        starter=True):
    asset_key = "weapon/" + weapon_id + "/"
    return {
        "id": weapon_id,
        "name": {"zh_cn": zh_name, "en": en_name},
        "description": {
            "zh_cn": "拥有清楚空间职责、成长节点与构筑协同的自动武器。",
            "en": "An automatic weapon with a readable spatial role and build synergies.",
        },
        "icon": asset_path(asset_key + "icon"),
        "starterEligible": bool(starter),
        "maxLevel": 10,
        "rarityWeight": 1.0,
        "behavior": behavior,
        "tags": tuple(tags),
        "baseDamage": float(base_damage),
        "cooldown": float(cooldown),
        "area": float(area),
        "speed": float(speed),
        "duration": float(duration),
        "amount": int(amount),
        "pierce": int(pierce),
        "bounce": int(bounce),
        "knockback": float(knockback),
        "hitboxDelay": float(hitbox_delay),
        "poolLimit": int(pool_limit),
        "visualPoolLimit": int(visual_limit),
        "projectilePrefab": (
            asset_path(asset_key + "projectile-prefab")
            if bHasProjectilePrefab else ""
        ),
        "castVfx": asset_path(asset_key + "cast-vfx"),
        "bodyVfx": asset_path(asset_key + "body-vfx"),
        "impactVfx": asset_path(asset_key + "impact-vfx"),
        "audioEvent": "weapon_" + weapon_id,
        "levelPlan": tuple(level_plan),
        "supportedStats": (
            "might", "haste", "reach", "quantity", "velocity", "duration",
        ),
        "unlockId": unlock_id,
        "evolutionId": evolution_id,
    }


WEAPONS = (
    _weapon("ring", "波纹环", "Ripple Ring", "expanding_ring", ("water", "area"), 19, 2.15, 4.0, 6.5, 0.9, 1, 99, 0, 0.34, 0.22, 4, 4, False, "quest_weapon_ring", "", _level_plan({"areaAdd": 0.6}, {"edgeWidthAdd": 0.18}, {"ringAdd": 1}, {"returnRing": True, "damageMultiplierAdd": 0.08})),
    _weapon("fireball", "火球", "Fireball", "lob_homing", ("fire", "projectile", "explosion"), 45, 2.6, 1.25, 12, 0.75, 1, 0, 0, 0.48, 0.15, 14, 12, True, "quest_weapon_fireball", "", _level_plan({"explosionAdd": 0.35}, {"amountAdd": 1}, {"homingTurnAdd": 0.35}, {"splitOnImpact": True}, 0.14, 0.035)),
    _weapon("moonblade", "月光刃", "Moon Blade", "fan_pierce", ("arcane", "projectile", "physical"), 36, 1.85, 1.0, 16, 0.7, 1, 8, 0, 0.68, 0.14, 18, 14, True, "quest_weapon_moonblade", "", _level_plan({"widthAdd": 0.25}, {"amountAdd": 1}, {"pierceAdd": 5}, {"crescentReturn": True}, 0.10, 0.04)),
    _weapon("bubble", "泡泡连弹", "Bubble Bounce", "bounce", ("water", "projectile", "control"), 22, 1.8, 0.8, 11, 1.1, 1, 0, 2, 0.30, 0.28, 22, 18, True, "quest_weapon_bubble", "royalbubblecade", _level_plan({"bounceAdd": 1}, {"slowAdd": 0.12}, {"bounceAdd": 2}, {"amountAdd": 1, "largeLastBounce": True}, 0.09, 0.035)),
    _weapon("aura", "灵光齐射", "Wisp Volley", "homing_volley", ("arcane", "projectile"), 18, 1.55, 0.5, 13, 0.9, 3, 0, 0, 0.25, 0.16, 28, 22, True, "quest_weapon_aura", "", _level_plan({"amountAdd": 1}, {"retarget": True}, {"amountAdd": 1}, {"orbitBeforeLaunch": True})),
    _weapon("dagger", "星光飞刀", "Star Daggers", "fan_projectile", ("physical", "projectile"), 12, 0.92, 0.34, 22, 0.65, 2, 1, 0, 0.22, 0.16, 42, 28, True, "quest_weapon_dagger", "nebulanetwork", _level_plan({"amountAdd": 1}, {"pierceAdd": 1}, {"spreadAdd": 0.14}, {"doubleFan": True}, 0.10, 0.03)),
    _weapon("starwheel", "星轮", "Star Wheel", "returning", ("physical", "projectile", "return"), 31, 2.25, 0.65, 15, 1.0, 1, 6, 0, 0.45, 0.22, 18, 14, True, "quest_weapon_starwheel", "", _level_plan({"rangeAdd": 2.0}, {"returnDamageAdd": 0.40}, {"amountAdd": 1}, {"orbitTurn": True})),
    _weapon("petalstorm", "花瓣新星", "Petal Nova", "radial_projectile", ("nature", "projectile", "area"), 17, 2.15, 0.5, 12, 1.0, 8, 1, 0, 0.28, 0.20, 40, 30, True, "quest_weapon_petalstorm", "galaxygarden", _level_plan({"amountAdd": 2}, {"pierceAdd": 1}, {"outerRing": True}, {"inwardBloom": True}, 0.10, 0.035)),
    _weapon("comet", "彗星合唱", "Comet Choir", "homing_volley", ("arcane", "projectile"), 24, 1.65, 0.55, 14, 1.0, 2, 0, 0, 0.32, 0.18, 28, 22, True, "quest_weapon_comet", "supernovachoir", _level_plan({"amountAdd": 1}, {"targetSpread": True}, {"amountAdd": 1}, {"orbitImpact": True})),
    _weapon("honeyneedle", "蜜糖蜂针", "Honey Needle", "fan_projectile", ("nature", "projectile", "mark"), 9, 0.78, 0.28, 18, 0.7, 3, 1, 0, 0.18, 0.12, 48, 34, True, "quest_weapon_honeyneedle", "royalbeehive", _level_plan({"amountAdd": 1}, {"honeyBurst": 18, "slow": 0.20}, {"pierceAdd": 1}, {"doubleVolley": True}, 0.09, 0.025)),
    _weapon("sporecap", "星孢菇帽", "Sporecap", "lob_zone", ("poison", "zone", "projectile"), 18, 2.4, 1.8, 8, 3.0, 1, 0, 0, 0.30, 0.5, 18, 14, True, "quest_weapon_sporecap", "myceliumcarnival", _level_plan({"areaAdd": 0.35, "durationAdd": 0.5}, {"poisonKillSpread": True}, {"amountAdd": 1}, {"splitCount": 3})),
    _weapon("phantombell", "幻影铃", "Phantom Bell", "echo_ring", ("arcane", "area", "echo"), 24, 2.6, 2.6, 0, 1.3, 1, 99, 0, 0.20, 0.32, 8, 8, True, "quest_weapon_phantombell", "midnightencore", _level_plan({"areaAdd": 0.4}, {"echoDamage": 0.75}, {"echoAdd": 1}, {"echoPull": 0.35, "damageMultiplierAdd": 0.08})),
    _weapon("coralanchor", "珊瑚锚", "Coral Anchor", "returning_lob", ("water", "physical", "return", "control"), 30, 2.85, 0.9, 10, 1.2, 1, 8, 0, 0.65, 0.22, 18, 14, True, "quest_weapon_coralanchor", "tidalfortress", _level_plan({"widthAdd": 0.25}, {"returnHit": True}, {"amountAdd": 1}, {"tidePoolDuration": 2.0})),
    _weapon("prismorbit", "星虹棱镜", "Prism Orbit", "orbit_beam", ("arcane", "beam", "orbit"), 8, 3.2, 0.32, 0, 1.8, 1, 2, 0, 0.10, 0.20, 12, 10, True, "quest_weapon_prismorbit", "friendshipspectrum", _level_plan({"durationAdd": 0.6}, {"amountAdd": 1}, {"pierceAdd": 2}, {"radialRefraction": True})),
    _weapon("acornmortar", "橡果迫击", "Acorn Mortar", "lob_split", ("nature", "projectile", "explosion"), 30, 2.9, 2.0, 8, 1.0, 1, 0, 3, 0.42, 0.22, 28, 20, True, "quest_weapon_acornmortar", "", _level_plan({"splitAdd": 1}, {"splitBounceAdd": 1}, {"amountAdd": 1}, {"splitCount": 7})),
    _weapon("frostorb", "雪糖晶球", "Frost Orb", "orbit_contact", ("ice", "orbit", "control"), 12, 0.55, 0.45, 4, 999, 3, 99, 0, 0.25, 0.55, 12, 12, True, "quest_weapon_frostorb", "", _level_plan({"amountAdd": 1}, {"freezeChanceAdd": 0.10, "freezeDurationAdd": 0.3}, {"orbitSwitch": True}, {"iceShardPerOrbit": True})),
    _weapon("gravityyoyo", "重力溜溜球", "Gravity Yo-Yo", "returning", ("arcane", "physical", "return", "control"), 24, 2.05, 0.55, 14, 1.1, 1, 5, 0, 0.45, 0.18, 24, 18, True, "quest_weapon_gravityyoyo", "", _level_plan({"rangeAdd": 2.0}, {"returnDamageAdd": 0.50}, {"amountAdd": 1}, {"damageLine": True})),
    _weapon("rainbowrail", "彩虹轨道炮", "Rainbow Rail", "telegraphed_beam", ("beam", "arcane", "telegraph"), 68, 4.6, 0.55, 0, 0.3, 1, 99, 0, 0.20, 0.55, 6, 6, True, "quest_weapon_rainbowrail", "", _level_plan({"widthAdd": 0.18}, {"crowdCooldownRefund": 0.20}, {"parallelBeamAdd": 1}, {"endExplosion": 55})),
)

WEAPON_BY_ID = {entry["id"]: entry for entry in WEAPONS}


EVOLUTIONS = (
    ("supernovachoir", "超新星合唱", "Supernova Choir", "comet", "velocity", "orbit_split"),
    ("royalbubblecade", "皇家泡泡巡游", "Royal Bubblecade", "bubble", "magnet", "capture_shield"),
    ("nebulanetwork", "星云针线", "Nebula Network", "dagger", "quantity", "stitch_lines"),
    ("galaxygarden", "银河花园", "Galaxy Garden", "petalstorm", "reach", "delayed_inward_bloom"),
    ("royalbeehive", "皇家蜂巢", "Royal Beehive", "honeyneedle", "haste", "hex_mark_burst"),
    ("myceliumcarnival", "菌星嘉年华", "Mycelium Carnival", "sporecap", "growth", "mycelium_links"),
    ("midnightencore", "午夜返场", "Midnight Encore", "phantombell", "fortune", "crit_note_encore"),
    ("tidalfortress", "潮汐堡垒", "Tidal Fortress", "coralanchor", "guard", "absorb_retaliate"),
    ("friendshipspectrum", "友谊光谱", "Friendship Spectrum", "prismorbit", "might", "tag_refraction"),
)
EVOLUTIONS = tuple({
    "id": row[0],
    "name": {"zh_cn": row[1], "en": row[2]},
    "weaponId": row[3],
    "tomeId": row[4],
    "requiredWeaponLevel": 10,
    "requiredTomeLevel": 5,
    "behavior": row[5],
    "icon": asset_path("evolution/" + row[0] + "/icon"),
    "chestTier": 2,
} for row in EVOLUTIONS)
EVOLUTION_BY_ID = {entry["id"]: entry for entry in EVOLUTIONS}


def _tome(
        tome_id, zh_name, en_name, effect,
        zh_effect, en_effect, cap, unlock_id):
    return {
        "id": tome_id,
        "name": {"zh_cn": zh_name, "en": en_name},
        "description": {"zh_cn": zh_effect, "en": en_effect},
        "maxLevel": 5,
        "effect": effect,
        "statText": {"zh_cn": zh_effect, "en": en_effect},
        "cap": cap,
        "rarityWeight": 1.0,
        "icon": asset_path("tome/" + tome_id + "/icon"),
        "unlockId": unlock_id,
    }


TOMES = (
    _tome("magnet", "引力绘本", "Magnet Tome", "pickupRange +18%/level", "拾取范围每级 +18%", "Pickup range +18% per level", 0.90, "quest_start"),
    _tome("vitality", "活力绘本", "Vitality Tome", "maxHealth +8%/level; heal new max 8%", "最大生命每级 +8%；升级时恢复新增生命上限的 8%", "Max health +8% per level; heal 8% of the new maximum", 0.40, "quest_start"),
    _tome("guard", "守护绘本", "Guard Tome", "damageReduction +6%/level", "伤害减免每级 +6%", "Damage reduction +6% per level", 0.30, "quest_start"),
    _tome("might", "力量绘本", "Might Tome", "weaponDamage +8%/level", "武器伤害每级 +8%", "Weapon damage +8% per level", 0.40, "quest_start"),
    _tome("haste", "迅捷绘本", "Haste Tome", "cooldown -5%/level", "冷却时间每级 -5%", "Cooldown -5% per level", 0.25, "quest_start"),
    _tome("reach", "辽阔绘本", "Reach Tome", "areaRange +7%/level", "范围与射程每级 +7%", "Area and range +7% per level", 0.35, "quest_start"),
    _tome("fortune", "幸运绘本", "Fortune Tome", "crit +3%, multiplier +0.08/level", "暴击率每级 +3%，暴击倍率每级 +0.08", "Critical chance +3% and multiplier +0.08 per level", 0.15, "quest_tome_fortune"),
    _tome("growth", "成长绘本", "Growth Tome", "xpGain +7%/level", "经验获取每级 +7%", "XP gain +7% per level", 0.35, "quest_start"),
    _tome("quantity", "花簇绘本", "Quantity Tome", "compatible quantity +1 at L1/L3/L5", "兼容武器在 1/3/5 级时数量 +1", "Compatible weapons gain +1 quantity at levels 1/3/5", 3, "quest_tome_quantity"),
    _tome("velocity", "流星绘本", "Velocity Tome", "projectileSpeed +12%/level", "弹体速度每级 +12%", "Projectile speed +12% per level", 0.60, "quest_start"),
    _tome("duration", "长夜绘本", "Duration Tome", "duration +12%/level", "持续时间每级 +12%", "Duration +12% per level", 0.60, "quest_tome_duration"),
    _tome("recovery", "复苏绘本", "Recovery Tome", "recovery +0.20 HP/s/level", "生命恢复每级 +0.20/秒", "Recovery +0.20 HP/s per level", 1.0, "quest_tome_recovery"),
    _tome("thorns", "荆棘绘本", "Thorns Tome", "thorns +6/level", "荆棘反伤每级 +6", "Thorns damage +6 per level", 30, "quest_tome_thorns"),
    _tome("greed", "丰收绘本", "Greed Tome", "run and result gold +8%/level", "本局与结算金币每级 +8%", "Run and result gold +8% per level", 0.40, "quest_tome_greed"),
    _tome("status", "异彩绘本", "Status Tome", "status damage/duration +10%/level", "状态伤害与持续时间每级 +10%", "Status damage and duration +10% per level", 0.50, "quest_tome_status"),
    _tome("curse", "诅咒绘本", "Curse Tome", "enemy pressure for XP and gold", "提高敌人压力，换取更多经验与金币", "Increase enemy pressure for more XP and gold", 0.50, "quest_clear_adventure"),
)
TOME_BY_ID = {entry["id"]: entry for entry in TOMES}


_TRINKET_ROWS = (
    ("prism_lens", "棱镜镜片", "Prism Lens", "命中时有 16% 概率分裂至最多两个附近目标，造成 35% 伤害。", "Hits have a 16% chance to split to up to two nearby targets for 35% damage.", "projectile_split", "quest_start"),
    ("popcorn_kernel", "星爆米花", "Popcorn Kernel", "爆炸与区域武器范围 +30%，伤害 -8%。", "Explosion and zone weapons gain 30% area but deal 8% less damage.", "area_tradeoff", "quest_trinket_popcorn"),
    ("sticky_honey", "黏黏蜜", "Sticky Honey", "武器命中会施加 12% 减速，持续 1.4 秒。", "Weapon hits apply a 12% slow for 1.4 seconds.", "stacking_slow", "quest_start"),
    ("echo_shell", "回声贝壳", "Echo Shell", "每第 7 次武器施放会以 45% 强度回响一次。", "Every seventh weapon cast echoes at 45% strength.", "seventh_cast_echo", "quest_trinket_echo"),
    ("lucky_ribbon", "幸运丝带", "Lucky Ribbon", "暴击击杀有 8% 概率获得 1 金币，每秒最多触发 3 次。", "Critical kills have an 8% chance to grant 1 gold, up to three times per second.", "crit_kill_gold", "quest_trinket_ribbon"),
    ("tiny_magnet", "袖珍磁铁", "Tiny Magnet", "连续拾取星光会累积短暂的磁力层数。", "Collecting starlight builds temporary magnet stacks.", "pickup_combo", "quest_start"),
    ("glass_star", "玻璃星", "Glass Star", "最大生命 -20%；满生命时伤害 +40%。", "Maximum health -20%; damage +40% while at full health.", "full_health_damage", "quest_trinket_glass"),
    ("marshmallow_shield", "棉花糖盾", "Marshmallow Shield", "抵挡下一次命中，消耗后 45 秒恢复。", "Blocks the next hit and recharges after 45 seconds.", "periodic_guard", "quest_start"),
    ("boss_bell", "强敌铃", "Boss Bell", "对精英与首领伤害 +28%，普通敌人伤害 -5%；首领宝箱金币 +20%。", "Deal 28% more damage to elites and bosses, 5% less to normal enemies, and gain 20% more boss-chest gold.", "boss_tradeoff", "quest_trinket_boss"),
    ("bloom_battery", "花火电池", "Bloom Battery", "区域持续伤害触发间隔 -18%，持续时间 -10%。", "Zone damage ticks 18% faster but lasts 10% less time.", "tick_tradeoff", "quest_trinket_battery"),
    ("comet_tail", "彗星尾", "Comet Tail", "弹体速度加成会转化为额外伤害，最高 +24%。", "Projectile-speed bonuses convert into damage, up to +24%.", "speed_conversion", "quest_trinket_tail"),
    ("friendship_pin", "友谊徽章", "Friendship Pin", "当前等级最低的武器数量 +1。", "Your lowest-level weapon gains +1 quantity.", "lowest_weapon_bonus", "quest_trinket_friendship"),
)
TRINKETS = tuple({
    "id": row[0],
    "name": {"zh_cn": row[1], "en": row[2]},
    "description": {"zh_cn": row[3], "en": row[4]},
    "behavior": row[5],
    "rarityWeight": 1.0,
    "icon": asset_path("trinket/" + row[0] + "/icon"),
    "unlockId": row[6],
    "hooks": (row[5],),
} for row in _TRINKET_ROWS)
TRINKET_BY_ID = {entry["id"]: entry for entry in TRINKETS}
