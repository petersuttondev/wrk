from datetime import UTC, datetime as DateTime, timedelta as TimeDelta
import signal
from sqlite3 import Connection
import sys
from typing import Final

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from wrk._database import (
    Event,
    StartEvent,
    StopEvent,
    insert_event,
    open_database,
)


class State:
    def __init__(self) -> None:
        self.timeline: Final[list[Event]] = []

    @property
    def is_started(self) -> bool:
        return bool(self.timeline) and isinstance(self.timeline[-1], StartEvent)

    def duration(self) -> TimeDelta:
        start: DateTime | None = None
        duration = TimeDelta()
        for event in self.timeline:
            match event:
                case StartEvent(timestamp=start):
                    pass
                case StopEvent(timestamp=stop):
                    if start is None:
                        raise ValueError()
                    duration += stop - start
                    start = None
        if start is not None:
            duration += DateTime.now(UTC) - start
            start = None
        return duration

    def start(self) -> StartEvent:
        event = StartEvent(DateTime.now(UTC))
        self.timeline.append(event)
        return event

    def stop(self) -> StopEvent:
        event = StopEvent(DateTime.now(UTC))
        self.timeline.append(event)
        return event


def _with_database_main(conn: Connection, state: State) -> None:
    app = QApplication(sys.argv)

    def handle_sigint(*_: object) -> None:
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)
    window = QMainWindow()
    window.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    window.setStyleSheet('background-color: red;')
    window.show()
    layout = QVBoxLayout()
    window.setLayout(layout)
    font = app.font()
    font.setFamily('DSEG7 Classic')
    font.setPointSize(24)
    font.setWeight(QFont.Weight.Bold)
    label = QLabel()
    label.setFont(font)

    def set_label_text() -> None:
        s = round(state.duration().total_seconds())
        h, s = divmod(s, 3_600)
        m, s = divmod(s, 60)
        label.setText(f'{h:02d}:{m:02d}:{s:02d}')

    set_label_text()
    layout.addWidget(label)

    def handle_toggle_click() -> None:
        if state.is_started:
            insert_event(conn, state.stop())
            window.setStyleSheet('background-color: red;')
        else:
            insert_event(conn, state.start())
            window.setStyleSheet('background-color: lime;')

    timer = QTimer(interval=1_000 // 2)
    timer.timeout.connect(set_label_text)
    timer.start()
    widget = QWidget()
    widget.setLayout(layout)
    window.setCentralWidget(widget)
    window.setFixedSize(layout.sizeHint())
    shortcut = QShortcut(QKeySequence('Space'), window)
    shortcut.activated.connect(handle_toggle_click)
    screen = app.screens()[0]
    g = screen.availableGeometry()
    wg = window.geometry()
    x = g.width() - wg.width()
    window.move(x, 0)
    app.exec()


def run_ui() -> None:
    state = State()
    with open_database() as conn:
        try:
            _with_database_main(conn, state)
        finally:
            if state.is_started:
                insert_event(conn, state.stop())
