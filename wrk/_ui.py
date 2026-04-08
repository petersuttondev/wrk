from datetime import UTC, datetime as DateTime, timedelta as TimeDelta
from pathlib import Path
import signal
from sqlite3 import Connection
import sys
from typing import Final, final, override

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
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
    fetch_events,
    insert_event,
    open_cursor,
    open_database,
)


class State:
    def __init__(self) -> None:
        self.events: Final[list[Event]] = []

    @property
    def is_started(self) -> bool:
        return bool(self.events) and isinstance(self.events[-1], StartEvent)

    def duration(self) -> TimeDelta:
        start: DateTime | None = None
        duration = TimeDelta()
        for event in self.events:
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
        self.events.append(event)
        return event

    def stop(self) -> StopEvent:
        event = StopEvent(DateTime.now(UTC))
        self.events.append(event)
        return event


@final
class _Label:
    @override
    def __init__(self, state: State, font: QFont) -> None:
        self.state: Final = state
        self.widget: Final = QLabel()
        self.widget.setFont(font)
        self.update()

    def update(self) -> None:
        s = round(self.state.duration().total_seconds())
        h, s = divmod(s, 3_600)
        m, s = divmod(s, 60)
        self.widget.setText(f'{h:02d}:{m:02d}:{s:02d}')


def _with_database_main(conn: Connection, state: State) -> None:
    app = QApplication(sys.argv)

    def handle_sigint(*_: object) -> None:
        app.quit()

    signal.signal(signal.SIGINT, handle_sigint)
    font = app.font()
    font.setFamily('DSEG7 Classic')
    font.setPointSize(12)
    font.setWeight(QFont.Weight.Bold)
    label = _Label(state, font)
    layout = QVBoxLayout()
    layout.addWidget(label.widget)
    widget = QWidget()
    widget.setLayout(layout)
    window = QMainWindow()

    def set_window_color(color: str) -> None:
        window.setStyleSheet(f'background-color: {color};')

    set_window_color('red')
    window.show()
    window.setCentralWidget(widget)
    window.setFixedSize(widget.sizeHint())
    screen_width = app.screens()[0].availableVirtualGeometry().width()
    window_width = window.geometry().width()
    window.move(screen_width - window_width, 0)
    media = QMediaPlayer(window)
    audio_output = QAudioOutput(parent=window)
    media.setAudioOutput(audio_output)
    parent_dir = Path(__file__).resolve(strict=True).parent
    media.setSource(QUrl.fromLocalFile(str(parent_dir / 'alert.wav')))

    def handle_shortcut() -> None:
        media.play()
        if state.is_started:
            insert_event(conn, state.stop())
            set_window_color('red')
        else:
            insert_event(conn, state.start())
            set_window_color('lime')

    shortcut = QShortcut(QKeySequence('Space'), window)
    shortcut.activated.connect(handle_shortcut)
    timer = QTimer(interval=1_000 // 2)
    timer.timeout.connect(label.update)
    timer.start()
    app.exec()


def run_ui() -> None:
    state = State()
    with open_database() as conn:
        with open_cursor(conn) as cursor:
            state.events.extend(fetch_events(cursor))
        try:
            _with_database_main(conn, state)
        finally:
            if state.is_started:
                insert_event(conn, state.stop())
