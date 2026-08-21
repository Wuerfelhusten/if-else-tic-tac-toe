from __future__ import annotations

import logging
from pathlib import Path
from time import perf_counter


EMPTY_BOARD = ("", "", "", "", "", "", "", "", "")
WIN_LINES = (
    (0, 1, 2),
    (3, 4, 5),
    (6, 7, 8),
    (0, 3, 6),
    (1, 4, 7),
    (2, 5, 8),
    (0, 4, 8),
    (2, 4, 6),
)
OUTPUT = Path(__file__).with_name("main.py")
SPLIT_DEPTHS = (3, 6)
LOGGER = logging.getLogger(__name__)


def outcome(board: tuple[str, ...]) -> tuple[str, tuple[int, ...]]:
    for first, second, third in WIN_LINES:
        if board[first] and board[first] == board[second] == board[third]:
            return board[first], (first, second, third)
    if "" not in board:
        return "draw", ()
    return "playing", ()


def describe_board(board: tuple[str, ...]) -> str:
    visible = tuple(value if value else "." for value in board)
    return " | ".join(
        " ".join(visible[start:start + 3]) for start in (0, 3, 6)
    )


def next_position(
    history: tuple[int, ...], board: tuple[str, ...], player: str, cell: int
) -> tuple[tuple[int, ...], tuple[str, ...], str, str, tuple[int, ...]]:
    next_history = history + (cell,)
    next_board = board[:cell] + (player,) + board[cell + 1:]
    status, winning_cells = outcome(next_board)
    next_player = "O" if player == "X" else "X"
    return next_history, next_board, next_player, status, winning_cells


def append_result(
    lines: list[str],
    indent: int,
    history: tuple[int, ...],
    board: tuple[str, ...],
    player: str,
    status: str,
    winning_cells: tuple[int, ...],
) -> None:
    prefix = " " * indent
    lines.extend(
        [
            f"{prefix}return (",
            f"{prefix}    {history!r},",
            f"{prefix}    {board!r},",
            f"{prefix}    {player!r}, {status!r}, {winning_cells!r},",
            f"{prefix})",
        ]
    )


def helper_name(history: tuple[int, ...]) -> str:
    return "_play_after_" + "_".join(str(cell + 1) for cell in history)


def render_move_choices(
    lines: list[str],
    history: tuple[int, ...],
    board: tuple[str, ...],
    player: str,
    indent: int,
) -> None:
    prefix = " " * indent
    free_cells = [cell for cell, value in enumerate(board) if value == ""]
    for move_number, cell in enumerate(free_cells):
        keyword = "if" if move_number == 0 else "elif"
        transition = next_position(history, board, player, cell)
        row, column = divmod(cell, 3)
        lines.append(
            f"{prefix}# Place {player} in cell {cell + 1} "
            f"(row {row + 1}, column {column + 1})."
        )
        lines.append(f"{prefix}{keyword} cell == {cell}:")
        lines.append("")
        append_result(lines, indent + 4, *transition)
    lines.append(f"{prefix}# Reject an unavailable cell.")
    lines.append(f"{prefix}else:")
    lines.append("")
    append_result(lines, indent + 4, history, board, player, "invalid", ())


def render_history_routes(
    lines: list[str],
    history: tuple[int, ...],
    board: tuple[str, ...],
    player: str,
    indent: int,
    opening_cells: tuple[int, ...] | None,
    helpers: list[tuple[tuple[int, ...], tuple[str, ...], str]],
    allow_split: bool,
) -> None:
    prefix = " " * indent
    free_cells = [cell for cell, value in enumerate(board) if value == ""]
    if not history and opening_cells is not None:
        free_cells = [cell for cell in free_cells if cell in opening_cells]

    for route_number, cell in enumerate(free_cells):
        keyword = "if" if route_number == 0 else "elif"
        next_history, next_board, next_player, status, _ = next_position(
            history, board, player, cell
        )
        row, column = divmod(cell, 3)
        lines.append(
            f"{prefix}# Follow {player} in cell {cell + 1}."
        )
        lines.append(f"{prefix}{keyword} history[{len(history)}] == {cell}:")
        lines.append("")
        if (
            status == "playing"
            and allow_split
            and len(next_history) in SPLIT_DEPTHS
        ):
            helpers.append((next_history, next_board, next_player))
            lines.append(
                f"{prefix}    return "
                f"{helper_name(next_history)}(history, cell)"
            )
        elif status == "playing":
            render_history_node(
                lines,
                next_history,
                next_board,
                next_player,
                indent + 4,
                opening_cells,
                helpers,
                allow_split,
            )
        else:
            append_result(
                lines,
                indent + 4,
                history,
                next_board,
                next_player,
                "invalid",
                (),
            )

    lines.append(f"{prefix}# Reject an impossible history.")
    lines.append(f"{prefix}else:")
    lines.append("")
    append_result(lines, indent + 4, history, board, player, "invalid", ())


def render_history_node(
    lines: list[str],
    history: tuple[int, ...],
    board: tuple[str, ...],
    player: str,
    indent: int,
    opening_cells: tuple[int, ...] | None,
    helpers: list[tuple[tuple[int, ...], tuple[str, ...], str]],
    allow_split: bool,
) -> None:
    prefix = " " * indent
    lines.append(f"{prefix}# Continue history {history!r}.")
    lines.append(f"{prefix}if len(history) == {len(history)}:")
    lines.append("")
    render_move_choices(lines, history, board, player, indent + 4)
    lines.append(f"{prefix}# Continue down the chronological game tree.")
    lines.append(f"{prefix}else:")
    lines.append("")
    render_history_routes(
        lines,
        history,
        board,
        player,
        indent + 4,
        opening_cells,
        helpers,
        allow_split,
    )


def render_engine(opening_cells: tuple[int, ...] | None = None) -> list[str]:
    lines = [
        "def play(history: History, cell: int) -> MoveResult:",
        '    """Advance a branch of the expanded chronological game tree."""',
    ]
    helpers: list[tuple[tuple[int, ...], tuple[str, ...], str]] = []
    render_history_node(
        lines, (), EMPTY_BOARD, "X", 4, opening_cells, helpers, True
    )
    for history, board, player in helpers:
        lines.extend(
            [
                "",
                "",
                f"def {helper_name(history)}("
                "history: History, cell: int) -> MoveResult:",
                f'    """Continue the game tree after history {history!r}."""',
            ]
        )
        render_history_node(
            lines,
            history,
            board,
            player,
            4,
            opening_cells,
            helpers,
            True,
        )
    return lines


UI_CODE = '''
class GameWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.history = ()
        self.board = EMPTY_BOARD
        self.player = "X"
        self.game_over = False
        self.setWindowTitle("If / Else Tic-Tac-Toe")
        self.setMinimumSize(460, 590)
        self.resize(520, 660)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(42, 34, 42, 38)
        layout.setSpacing(22)

        title_row = QHBoxLayout()
        title = QLabel("TIC-TAC-TOE")
        title.setObjectName("title")
        mode = QLabel("IF / ELSE EDITION")
        mode.setObjectName("mode")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(mode)
        layout.addLayout(title_row)

        self.status = QLabel("X to move")
        self.status.setObjectName("status")
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

        board_frame = QFrame()
        board_frame.setObjectName("board")
        grid = QGridLayout(board_frame)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(8)

        self.cell0 = self._make_cell(0)
        self.cell1 = self._make_cell(1)
        self.cell2 = self._make_cell(2)
        self.cell3 = self._make_cell(3)
        self.cell4 = self._make_cell(4)
        self.cell5 = self._make_cell(5)
        self.cell6 = self._make_cell(6)
        self.cell7 = self._make_cell(7)
        self.cell8 = self._make_cell(8)
        grid.addWidget(self.cell0, 0, 0)
        grid.addWidget(self.cell1, 0, 1)
        grid.addWidget(self.cell2, 0, 2)
        grid.addWidget(self.cell3, 1, 0)
        grid.addWidget(self.cell4, 1, 1)
        grid.addWidget(self.cell5, 1, 2)
        grid.addWidget(self.cell6, 2, 0)
        grid.addWidget(self.cell7, 2, 1)
        grid.addWidget(self.cell8, 2, 2)
        layout.addWidget(board_frame, 1)

        restart = QPushButton("New Game")
        restart.setObjectName("restart")
        restart.setCursor(Qt.CursorShape.PointingHandCursor)
        restart.clicked.connect(self.reset_game)
        layout.addWidget(restart)
        self.setCentralWidget(root)

    def _make_cell(self, index: int) -> QPushButton:
        button = QPushButton()
        button.setObjectName("cell")
        button.setProperty("mark", "empty")
        button.setMinimumSize(100, 100)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        button.clicked.connect(
            lambda checked=False, cell=index: self.play_cell(cell)
        )
        return button

    def _button_for(self, cell: int) -> QPushButton:
        # Return the button in the first cell.
        if cell == 0:

            return self.cell0
        # Return the button in the second cell.
        elif cell == 1:

            return self.cell1
        # Return the button in the third cell.
        elif cell == 2:

            return self.cell2
        # Return the button in the fourth cell.
        elif cell == 3:

            return self.cell3
        # Return the button in the fifth cell.
        elif cell == 4:

            return self.cell4
        # Return the button in the sixth cell.
        elif cell == 5:

            return self.cell5
        # Return the button in the seventh cell.
        elif cell == 6:

            return self.cell6
        # Return the button in the eighth cell.
        elif cell == 7:

            return self.cell7
        # Return the final button for the remaining valid index.
        else:

            return self.cell8

    def play_cell(self, cell: int) -> None:
        # Ignore input after the current round has ended.
        if self.game_over:

            return
        next_history, next_board, next_player, result, winning_cells = play(
            self.history, cell
        )
        # Ignore occupied cells and invalid board states.
        if result == "invalid":

            return

        button = self._button_for(cell)
        button.setText(self.player)
        button.setProperty("mark", self.player.lower())
        button.setEnabled(False)
        button.style().unpolish(button)
        button.style().polish(button)
        self.history = next_history
        self.board = next_board
        self.player = next_player

        # Finish the round when either player completes a winning line.
        if result == "X" or result == "O":

            self.game_over = True
            self.status.setText(f"{result} wins")
            self.status.setProperty("state", "won")
            self._highlight_winner(winning_cells)
            self._disable_board()
        # Finish the round when the final move produces no winner.
        elif result == "draw":

            self.game_over = True
            self.status.setText("Draw")
            self.status.setProperty("state", "draw")
            self._disable_board()
        # Continue with the next player's turn.
        else:

            self.status.setText(f"{self.player} to move")

        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _highlight_winner(self, cells: tuple[int, ...]) -> None:
        self._set_winner(cells[0])
        self._set_winner(cells[1])
        self._set_winner(cells[2])

    def _set_winner(self, cell: int) -> None:
        button = self._button_for(cell)
        button.setProperty("winner", True)
        button.style().unpolish(button)
        button.style().polish(button)

    def _disable_board(self) -> None:
        self.cell0.setEnabled(False)
        self.cell1.setEnabled(False)
        self.cell2.setEnabled(False)
        self.cell3.setEnabled(False)
        self.cell4.setEnabled(False)
        self.cell5.setEnabled(False)
        self.cell6.setEnabled(False)
        self.cell7.setEnabled(False)
        self.cell8.setEnabled(False)

    def reset_game(self) -> None:
        self.history = ()
        self.board = EMPTY_BOARD
        self.player = "X"
        self.game_over = False
        self.status.setText("X to move")
        self.status.setProperty("state", "playing")
        self._reset_button(self.cell0)
        self._reset_button(self.cell1)
        self._reset_button(self.cell2)
        self._reset_button(self.cell3)
        self._reset_button(self.cell4)
        self._reset_button(self.cell5)
        self._reset_button(self.cell6)
        self._reset_button(self.cell7)
        self._reset_button(self.cell8)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def _reset_button(self, button: QPushButton) -> None:
        button.setText("")
        button.setEnabled(True)
        button.setProperty("mark", "empty")
        button.setProperty("winner", False)
        button.style().unpolish(button)
        button.style().polish(button)


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(
        """
        QWidget#root { background: #111318; color: #f1f4f8; }
        QLabel#title { color: #f1f4f8; font-size: 23px; font-weight: 800; }
        QLabel#mode {
            color: #9ca8b8; background: #1c2028;
            border: 1px solid #303744; border-radius: 4px;
            padding: 7px 10px; font-size: 11px; font-weight: 700;
        }
        QLabel#status {
            background: #181c23; border-left: 3px solid #35c2a0;
            color: #dce3ec; padding: 13px; font-size: 17px;
            font-weight: 600;
        }
        QLabel#status[state="won"] {
            border-left-color: #f2c14e; color: #f6d77f;
        }
        QLabel#status[state="draw"] { border-left-color: #8491a3; }
        QFrame#board { background: #0b0d11; border: 1px solid #292f39; }
        QPushButton#cell {
            background: #191d24; border: 1px solid #303742;
            border-radius: 5px; color: #edf2f7;
        }
        QPushButton#cell:hover { background: #222832; border-color: #4b5666; }
        QPushButton#cell:disabled { background: #171b21; }
        QPushButton#cell[mark="x"] { color: #54d6b7; }
        QPushButton#cell[mark="o"] { color: #ff7c8c; }
        QPushButton#cell[winner="true"] {
            background: #39331d; border: 2px solid #f2c14e;
            color: #f6d77f;
        }
        QPushButton#restart {
            min-height: 46px; background: #35c2a0; color: #08120f;
            border: none; border-radius: 5px; font-size: 15px;
            font-weight: 800;
        }
        QPushButton#restart:hover { background: #49d4b2; }
        QPushButton#restart:pressed { background: #2aa98b; }
        """
    )


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    started_at = perf_counter()
    app = QApplication(sys.argv)
    apply_theme(app)
    window = GameWindow()
    window.show()
    exit_code = app.exec()
    elapsed = perf_counter() - started_at
    LOGGER.info("Application ran for %.3f seconds.", elapsed)
    return exit_code
'''.strip()


def render_main(opening_cells: tuple[int, ...] | None = None) -> str:
    lines = [
        '"""Generated application. Run generator.py to rebuild it."""',
        "",
        "from __future__ import annotations",
        "",
        "import logging",
        "import sys",
        "from time import perf_counter",
        "",
        "from PySide6.QtCore import Qt",
        "from PySide6.QtGui import QFont",
        "from PySide6.QtWidgets import (",
        "    QApplication,",
        "    QFrame,",
        "    QGridLayout,",
        "    QHBoxLayout,",
        "    QLabel,",
        "    QMainWindow,",
        "    QPushButton,",
        "    QVBoxLayout,",
        "    QWidget,",
        ")",
        "",
        "",
        'EMPTY_BOARD = ("", "", "", "", "", "", "", "", "")',
        "History = tuple[int, ...]",
        "Board = tuple[str, ...]",
        "MoveResult = tuple[History, Board, str, str, tuple[int, ...]]",
        "LOGGER = logging.getLogger(__name__)",
        "",
        "",
        *render_engine(opening_cells),
        "",
        "",
        UI_CODE,
        "",
        "",
        "# Launch only when the generated file is executed directly.",
        'if __name__ == "__main__":',
        "",
        "    raise SystemExit(main())",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    started_at = perf_counter()
    OUTPUT.write_text(render_main(), encoding="utf-8", newline="\n")
    elapsed = perf_counter() - started_at
    LOGGER.info(
        "Generated standalone %s with the complete chronological game tree "
        "in %.3f seconds.",
        OUTPUT.name,
        elapsed,
    )


if __name__ == "__main__":
    main()
