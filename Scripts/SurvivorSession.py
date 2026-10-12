"""Process-local handoff between the menu and gameplay Levels."""

MAIN_MENU_SCENE = "Assets/Scenes/MainMenu.he"
GAMEPLAY_SCENE = "Assets/Scenes/MainGame.he"

_pending_launch = None
_objective_diagnostic = {}


def stage_launch(character_id, difficulty_id, challenge_selection, run_seed):
    """Stage exactly one launch without replacing a pending scene request."""
    global _pending_launch
    if _pending_launch is not None:
        return False
    if not isinstance(character_id, str) or not character_id:
        raise ValueError("character_id must be a non-empty string")
    if not isinstance(difficulty_id, str) or not difficulty_id:
        raise ValueError("difficulty_id must be a non-empty string")
    if isinstance(challenge_selection, (list, tuple)):
        challenge_selection = list(challenge_selection)
    elif not isinstance(challenge_selection, str):
        raise ValueError("challenge_selection must be a string or sequence")
    _pending_launch = {
        "character_id": character_id,
        "difficulty_id": difficulty_id,
        "challenge_selection": challenge_selection,
        "run_seed": int(run_seed) & 0xFFFFFFFF,
    }
    return True


def consume_launch():
    global _pending_launch
    launch = _pending_launch
    _pending_launch = None
    return launch


def clear_launch():
    global _pending_launch
    _pending_launch = None


def has_pending_launch():
    return _pending_launch is not None


def publish_objective_diagnostic(snapshot):
    global _objective_diagnostic
    _objective_diagnostic = dict(snapshot or {})


def objective_diagnostic_snapshot():
    return dict(_objective_diagnostic)
