import HEngine
import SurvivorObjectives
import SurvivorProfile
import SurvivorSession


OWNER = "project.survivor.gm"
PROFILE_DOMAIN = "survivor.profile"
OBJECTIVE_DOMAIN = "survivor.objective"
PROFILE_PATH = HEngine.GetSavedPath("Config/SurvivorProgression.json")
_session_tainted = False


def _availability():
    return {"available": True}


def _snapshot_profile():
    return SurvivorProfile.load_profile(PROFILE_PATH)


def _snapshot_objective():
    snapshot = SurvivorSession.objective_diagnostic_snapshot()
    return snapshot or SurvivorObjectives.current_objective_diagnostic()


def _reject_objective_commit(_state):
    return {
        "success": False,
        "message": "区域目标诊断是只读状态。",
    }


def _read_objective(_arguments, _staged_domains):
    return {
        "success": True,
        "message": "已读取四域净化运行状态。",
        "data": _snapshot_objective(),
    }


def _start_capture_scenario(arguments, _staged_domains):
    profile = _snapshot_profile()
    SurvivorSession.clear_launch()
    if not SurvivorSession.stage_launch(
            profile.get("selectedCharacter", "starpaw"),
            profile.get("selectedDifficulty", "adventure"),
            profile.get("selectedChallenges", ()),
            int(arguments.get("run_seed", 7319))):
        return {"success": False, "message": "开发场景启动请求已存在。"}
    if not HEngine.RequestRuntimeScene(SurvivorSession.GAMEPLAY_SCENE):
        SurvivorSession.clear_launch()
        return {"success": False, "message": "场景切换请求槽正忙。"}
    return {
        "success": True,
        "message": "已请求确定性 Survivor Gameplay 场景。",
        "data": {"scene": SurvivorSession.GAMEPLAY_SCENE},
    }


def _commit_profile(profile):
    saved = SurvivorProfile.save_profile(profile, PROFILE_PATH)
    return {
        "success": True,
        "message": "幸存者档案已原子提交。",
        "data": {"walletGold": saved["walletGold"]},
    }


def _restore_profile(profile):
    SurvivorProfile.save_profile(profile, PROFILE_PATH)
    return {"success": True, "message": "幸存者档案已回滚恢复。"}


def _refresh_profile():
    HEngine.HE_CORE_INFO("[GM] Survivor profile state refreshed.")


def _mark_tainted():
    global _session_tainted
    _session_tainted = True


def _add_gold(arguments, staged_domains):
    profile = staged_domains[PROFILE_DOMAIN]
    before = profile["walletGold"]
    after = min(SurvivorProfile.MAX_WALLET_GOLD, before + arguments["amount"])
    profile["walletGold"] = after
    return {"walletBefore": before, "walletAfter": after}


def _set_gold(arguments, staged_domains):
    profile = staged_domains[PROFILE_DOMAIN]
    before = profile["walletGold"]
    profile["walletGold"] = arguments["amount"]
    return {"walletBefore": before, "walletAfter": profile["walletGold"]}


def _unlock_content(arguments, staged_domains):
    profile = staged_domains[PROFILE_DOMAIN]
    category = arguments["category"]
    content_id = arguments["content_id"]
    eligible = profile["eligible"][category]
    owned = profile["owned"][category]
    if content_id not in eligible:
        eligible.append(content_id)
    if content_id not in owned:
        owned.append(content_id)
    return {"category": category, "contentId": content_id, "owned": True}


def _reset_profile(_arguments, staged_domains):
    staged_domains[PROFILE_DOMAIN] = SurvivorProfile.default_profile()
    return {"reset": True}


def register():
    HEngine.GM.UnregisterOwner(OWNER)
    HEngine.GM.RegisterStateDomain(
        OWNER,
        {
            "name": PROFILE_DOMAIN,
            "displayName": "幸存者档案",
            "summary": "以原子方式持久化的幸存者成长档案。",
            "persistent": True,
        },
        _snapshot_profile,
        _commit_profile,
        availability=_availability,
        restore=_restore_profile,
        refresh=_refresh_profile,
        mark_tainted=_mark_tainted,
    )
    HEngine.GM.RegisterStateDomain(
        OWNER,
        {
            "name": OBJECTIVE_DOMAIN,
            "displayName": "四域净化运行状态",
            "summary": "当前区域、怪潮、权能冷却和目标 Boss 的只读诊断。",
            "persistent": False,
        },
        _snapshot_objective,
        _reject_objective_commit,
        availability=_availability,
    )
    HEngine.GM.RegisterCommand(
        OWNER,
        {
            "name": "survivor.objective.snapshot",
            "displayName": "读取四域净化状态",
            "summary": "读取当前区域、进度、怪潮、权能与目标 Boss 状态。",
            "category": "幸存者 / 诊断",
            "scope": "read-only",
            "risk": "safe",
            "stateDomains": [],
            "taintsCurrentSession": False,
        },
        _read_objective,
    )
    HEngine.GM.RegisterCommand(
        OWNER,
        {
            "name": "survivor.capture.start",
            "displayName": "启动确定性幸存者场景",
            "summary": "使用当前 HE_SURVIVOR_CAPTURE_SCENARIO 直接进入 Gameplay。",
            "category": "幸存者 / 诊断",
            "scope": "session-control",
            "risk": "safe",
            "stateDomains": [],
            "taintsCurrentSession": False,
            "arguments": [
                {
                    "name": "run_seed",
                    "displayName": "固定种子",
                    "type": "integer",
                    "required": False,
                    "default": 7319,
                    "minimum": 0,
                    "maximum": 4294967295,
                }
            ],
        },
        _start_capture_scenario,
    )

    HEngine.GM.RegisterCommand(
        OWNER,
        {
            "name": "survivor.profile.add_gold",
            "displayName": "增加金币",
            "summary": "向暂存档案增加指定数量的金币。",
            "category": "幸存者 / 档案",
            "scope": "persistent-profile",
            "risk": "confirm",
            "stateDomains": [PROFILE_DOMAIN],
            "taintsCurrentSession": True,
            "arguments": [
                {
                    "name": "amount",
                    "displayName": "数量",
                    "summary": "增加后会限制在档案允许的金币上限内。",
                    "type": "integer",
                    "required": True,
                    "default": 100,
                    "minimum": 1,
                    "maximum": 1000000,
                }
            ],
        },
        _add_gold,
    )

    HEngine.GM.RegisterCommand(
        OWNER,
        {
            "name": "survivor.profile.set_gold",
            "displayName": "设置金币",
            "summary": "将暂存钱包余额设置为指定值。",
            "category": "幸存者 / 档案",
            "scope": "persistent-profile",
            "risk": "dangerous",
            "stateDomains": [PROFILE_DOMAIN],
            "taintsCurrentSession": True,
            "arguments": [
                {
                    "name": "amount",
                    "displayName": "钱包金币",
                    "type": "integer",
                    "required": True,
                    "default": 1000,
                    "minimum": 0,
                    "maximum": SurvivorProfile.MAX_WALLET_GOLD,
                }
            ],
        },
        _set_gold,
    )

    HEngine.GM.RegisterCommand(
        OWNER,
        {
            "name": "survivor.profile.unlock_content",
            "displayName": "解锁内容",
            "summary": "为指定内容 ID 授予解锁资格和所有权。",
            "category": "幸存者 / 档案",
            "scope": "persistent-profile",
            "risk": "dangerous",
            "stateDomains": [PROFILE_DOMAIN],
            "taintsCurrentSession": True,
            "arguments": [
                {
                    "name": "category",
                    "displayName": "类别",
                    "type": "enum",
                    "required": True,
                    "default": "characters",
                    "choices": ["characters", "weapons", "trinkets"],
                    "choiceLabels": ["角色", "武器", "奇物"],
                },
                {
                    "name": "content_id",
                    "displayName": "内容 ID",
                    "type": "string",
                    "required": True,
                    "maxLength": 128,
                },
            ],
        },
        _unlock_content,
    )

    HEngine.GM.RegisterCommand(
        OWNER,
        {
            "name": "survivor.profile.reset",
            "displayName": "重置档案",
            "summary": "使用经过校验的默认档案替换全部幸存者成长数据。",
            "category": "幸存者 / 档案",
            "scope": "persistent-profile",
            "risk": "dangerous",
            "stateDomains": [PROFILE_DOMAIN],
            "taintsCurrentSession": True,
        },
        _reset_profile,
    )
