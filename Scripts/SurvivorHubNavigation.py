"""Pure focus and repeat rules shared by the Survivor Hub gamepad path."""


DIRECTIONS = ("left", "right", "up", "down")


def focus_ids(rows):
    return tuple(item for row in rows for item in row if item)


def normalize_focus(rows, current, fallback=""):
    available = focus_ids(rows)
    if current in available:
        return current
    if fallback in available:
        return fallback
    return available[0] if available else ""


def move_focus(rows, current, direction):
    """Move in a ragged 2D focus grid without producing invisible focus."""

    if direction not in DIRECTIONS:
        return normalize_focus(rows, current)
    clean_rows = tuple(tuple(item for item in row if item) for row in rows)
    clean_rows = tuple(row for row in clean_rows if row)
    current = normalize_focus(clean_rows, current)
    if not current:
        return ""

    row_index = 0
    column_index = 0
    for index, row in enumerate(clean_rows):
        if current in row:
            row_index = index
            column_index = row.index(current)
            break

    if direction in ("left", "right"):
        row = clean_rows[row_index]
        offset = -1 if direction == "left" else 1
        return row[(column_index + offset) % len(row)]

    target_row_index = row_index + (-1 if direction == "up" else 1)
    target_row_index = max(0, min(len(clean_rows) - 1, target_row_index))
    target = clean_rows[target_row_index]
    source = clean_rows[row_index]
    if len(source) <= 1 or len(target) <= 1:
        target_column = 0
    else:
        normalized_column = column_index / float(len(source) - 1)
        target_column = int(round(normalized_column * (len(target) - 1)))
    return target[target_column]


def apply_deadzone(value, deadzone=0.20):
    value = max(-1.0, min(1.0, float(value)))
    magnitude = abs(value)
    if magnitude <= deadzone:
        return 0.0
    scaled = (magnitude - deadzone) / (1.0 - deadzone)
    return scaled if value > 0.0 else -scaled


def pressed_edges(previous, current):
    return {
        key for key, value in current.items()
        if value and not previous.get(key, False)
    }


class DirectionalRepeater:
    def __init__(
            self,
            enter_threshold=0.58,
            release_threshold=0.38,
            initial_delay=0.34,
            repeat_delay=0.10):
        self.enter_threshold = float(enter_threshold)
        self.release_threshold = float(release_threshold)
        self.initial_delay = float(initial_delay)
        self.repeat_delay = float(repeat_delay)
        self.direction = None
        self.timer = 0.0

    @staticmethod
    def _candidate(x_axis, y_axis, threshold):
        x_axis = float(x_axis)
        y_axis = float(y_axis)
        if max(abs(x_axis), abs(y_axis)) < threshold:
            return None
        if abs(x_axis) >= abs(y_axis):
            return "right" if x_axis > 0.0 else "left"
        return "up" if y_axis > 0.0 else "down"

    def reset(self):
        self.direction = None
        self.timer = 0.0

    def update(self, x_axis, y_axis, delta_seconds):
        threshold = (
            self.release_threshold if self.direction is not None
            else self.enter_threshold
        )
        candidate = self._candidate(x_axis, y_axis, threshold)
        if candidate is None:
            self.reset()
            return None
        if candidate != self.direction:
            self.direction = candidate
            self.timer = self.initial_delay
            return candidate

        self.timer -= max(0.0, min(float(delta_seconds), 0.10))
        if self.timer > 0.0:
            return None
        self.timer = self.repeat_delay
        return self.direction


class ActionDebouncer:
    """Reject repeated activation of the same UI action for a short interval."""

    def __init__(self, cooldown_seconds=0.35):
        self.cooldown_seconds = max(0.0, float(cooldown_seconds))
        self.timers = {}

    def update(self, delta_seconds):
        delta_seconds = max(0.0, float(delta_seconds))
        self.timers = {
            action_id: remaining
            for action_id, timer in self.timers.items()
            for remaining in (max(0.0, timer - delta_seconds),)
            if remaining > 0.0
        }

    def acquire(self, action_id):
        action_id = str(action_id)
        if self.timers.get(action_id, 0.0) > 0.0:
            return False
        self.timers[action_id] = self.cooldown_seconds
        return True
