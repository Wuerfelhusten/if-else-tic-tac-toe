from __future__ import annotations

import ast
import unittest

from generator import render_main


class GeneratedApplicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = render_main(opening_cells=(0,))
        namespace = {"__name__": "generated_test"}
        exec(compile(cls.source, "<generated-main>", "exec"), namespace)
        cls.play = staticmethod(namespace["play"])

    def test_x_wins_top_row(self) -> None:
        history = ()
        for cell in (0, 3, 1, 4):
            history, _, _, status, _ = self.play(history, cell)
            self.assertEqual("playing", status)
        _, _, player, status, winning = self.play(history, 2)
        self.assertEqual("X", status)
        self.assertEqual((0, 1, 2), winning)
        self.assertEqual("O", player)

    def test_draw(self) -> None:
        history = ()
        for cell in (0, 1, 2, 4, 3, 5, 7, 6):
            history, _, _, status, _ = self.play(history, cell)
            self.assertEqual("playing", status)
        _, _, _, status, winning = self.play(history, 8)
        self.assertEqual("draw", status)
        self.assertEqual((), winning)

    def test_occupied_cell_is_rejected(self) -> None:
        history, board, _, _, _ = self.play((), 0)
        result = self.play(history, 0)
        unchanged_history, unchanged, player, status, winning = result
        self.assertEqual(history, unchanged_history)
        self.assertEqual(board, unchanged)
        self.assertEqual("O", player)
        self.assertEqual("invalid", status)
        self.assertEqual((), winning)

    def test_generated_application_uses_no_loop_control_flow(self) -> None:
        tree = ast.parse(self.source)
        forbidden = (
            ast.For,
            ast.AsyncFor,
            ast.While,
            ast.Match,
            ast.Try,
            ast.With,
        )
        found = [
            type(node).__name__
            for node in ast.walk(tree)
            if isinstance(node, forbidden)
        ]
        self.assertEqual([], found)

    def test_every_generated_condition_has_an_english_comment(self) -> None:
        lines = self.source.splitlines()
        uncommented = []
        for line_number, line in enumerate(lines, start=1):
            statement = line.lstrip()
            if statement.startswith(("if ", "elif ")):
                previous = line_number - 2
                while previous >= 0 and not lines[previous].strip():
                    previous -= 1
                has_comment = (
                    previous >= 0
                    and lines[previous].lstrip().startswith("# ")
                )
                if not has_comment:
                    uncommented.append(line_number)
        self.assertEqual([], uncommented)
        self.assertIn("# Continue history", self.source)
        self.assertIn("# Place X in cell", self.source)

    def test_every_generated_branch_starts_with_a_blank_line(self) -> None:
        lines = self.source.splitlines()
        missing = []
        for line_number, line in enumerate(lines, start=1):
            statement = line.lstrip()
            if statement.startswith(("if ", "elif ", "else:")):
                if line_number >= len(lines) or lines[line_number].strip():
                    missing.append(line_number)
        self.assertEqual([], missing)

    def test_generated_lines_follow_pep8_width(self) -> None:
        long_lines = [
            (line_number, len(line))
            for line_number, line in enumerate(
                self.source.splitlines(), start=1
            )
            if len(line) > 79
        ]
        self.assertEqual([], long_lines)

    def test_generated_application_logs_its_runtime(self) -> None:
        self.assertIn("started_at = perf_counter()", self.source)
        self.assertIn(
            'LOGGER.info("Application ran for %.3f seconds.", elapsed)',
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
