
class Event:
    pass

class EventStop(Event):
    pass

class WindowEvent(Event):
    hwnd: int

    def __init__(self, hwnd):
        self.hwnd = hwnd

class EventCreateWindow(WindowEvent):
    pass

class EventDestroyWindow(WindowEvent):
    pass

class EventMoveSize(WindowEvent):
    rect: tuple[int, int, int, int]

    def __init__(self, hwnd, rect):
        super().__init__(hwnd)
        self.rect = rect

class EventActivate(WindowEvent):
    inactive: bool
    minimized: bool

    def __init__(self, hwnd, inactive, minimized):
        super().__init__(hwnd)
        self.inactive = bool(inactive)
        self.minimized = bool(minimized)
