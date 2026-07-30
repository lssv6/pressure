"""Application entry point."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from PySide6.QtWidgets import QApplication

from .sources import SIMULATED_PORT
from .ui.main_window import MainWindow
from .ui.theme import STYLESHEET

APPLICATION_NAME = "Dual HX710B Pressure Monitor"
ORGANISATION_NAME = "pressure-monitor"


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APPLICATION_NAME)
    parser.add_argument(
        "--port",
        help="serial port to preselect, or 'sim' for the built-in simulator",
    )
    parser.add_argument("--baud", type=int, help="serial baud rate to preselect")
    parser.add_argument(
        "--connect",
        action="store_true",
        help="connect to the selected port on startup",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parse_args(sys.argv[1:] if argv is None else argv)
    port = SIMULATED_PORT if arguments.port == "sim" else arguments.port

    app = QApplication(sys.argv[:1])
    app.setApplicationName(APPLICATION_NAME)
    app.setOrganizationName(ORGANISATION_NAME)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow(
        port=port, baud_rate=arguments.baud, autoconnect=arguments.connect
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
