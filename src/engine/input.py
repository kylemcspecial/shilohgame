"""Input handling: keyboard plus gamepad, unified into a simple action API."""
import pygame

UP = "up"
DOWN = "down"
LEFT = "left"
RIGHT = "right"
CONFIRM = "confirm"
CANCEL = "cancel"
MENU = "menu"
PAUSE = "pause"
FULLSCREEN = "fullscreen"

_KEY_MAP = {
    pygame.K_UP: UP,
    pygame.K_w: UP,
    pygame.K_DOWN: DOWN,
    pygame.K_s: DOWN,
    pygame.K_LEFT: LEFT,
    pygame.K_a: LEFT,
    pygame.K_RIGHT: RIGHT,
    pygame.K_d: RIGHT,
    pygame.K_z: CONFIRM,
    pygame.K_SPACE: CONFIRM,
    pygame.K_RETURN: MENU,
    pygame.K_KP_ENTER: MENU,
    pygame.K_x: CANCEL,
    pygame.K_BACKSPACE: CANCEL,
    pygame.K_ESCAPE: PAUSE,
}

_JOY_AXIS_MAP = {
    0: (LEFT, RIGHT),
    1: (UP, DOWN),
}
_JOY_BUTTON_MAP = {
    0: CONFIRM,   # A / cross
    1: CANCEL,     # B / circle
    6: PAUSE,      # back/select
    7: MENU,       # start
}
_JOY_HAT_ACTIONS = ((LEFT, RIGHT), (UP, DOWN))

_AXIS_DEADZONE = 0.5


class Input:
    """Tracks held actions and newly-pressed actions per frame."""

    def __init__(self):
        self.held = set()
        self.held_set = self.held  # alias for readability
        self.pressed = set()
        self._joysticks = {}

        self._init_joysticks()

    def _init_joysticks(self):
        for i in range(pygame.joystick.get_count()):
            stick = pygame.joystick.Joystick(i)
            stick.init()
            self._joysticks[stick.get_instance_id()] = stick

    def _joystick_actions(self):
        actions = set()
        for stick in self._joysticks.values():
            for axis, (neg, pos) in _JOY_AXIS_MAP.items():
                if axis >= stick.get_numaxes():
                    continue
                value = stick.get_axis(axis)
                if value < -_AXIS_DEADZONE:
                    actions.add(neg)
                elif value > _AXIS_DEADZONE:
                    actions.add(pos)
            if stick.get_numhats() > 0:
                hat_x, hat_y = stick.get_hat(0)
                if hat_x == -1:
                    actions.add(_JOY_HAT_ACTIONS[0][0])
                elif hat_x == 1:
                    actions.add(_JOY_HAT_ACTIONS[0][1])
                if hat_y == 1:
                    actions.add(_JOY_HAT_ACTIONS[1][0])
                elif hat_y == -1:
                    actions.add(_JOY_HAT_ACTIONS[1][1])
            for btn, action in _JOY_BUTTON_MAP.items():
                if btn < stick.get_numbuttons() and stick.get_button(btn):
                    actions.add(action)
        return actions

    def update(self, events):
        """Process events and refresh per-frame action sets."""
        previously_held = set(self.held)
        current = set()

        for event in events:
            if event.type == pygame.KEYDOWN:
                action = _KEY_MAP.get(event.key)
                if action:
                    current.add(action)
            elif event.type == pygame.JOYDEVICEADDED:
                stick = pygame.joystick.Joystick(event.device_index)
                stick.init()
                self._joysticks[stick.get_instance_id()] = stick
            elif event.type == pygame.JOYDEVICEREMOVED:
                stick = self._joysticks.pop(event.instance_id, None)
                if stick is not None:
                    stick.quit()

        keys = pygame.key.get_pressed()
        for key, action in _KEY_MAP.items():
            if keys[key]:
                current.add(action)

        current |= self._joystick_actions()

        self.held = current
        self.held_set = self.held
        self.pressed = current - previously_held

        return self.pressed
