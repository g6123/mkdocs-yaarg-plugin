"""
Provides base generator implementation and utilities to build generators.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional

from mkdocs.config import Config as MKDocsConfig
from schema import Schema


class BaseGenerator(ABC):
    """
    Base class for yaarg generators.
    """

    options_schema = Schema({})

    def __init__(self, mkdocs: MKDocsConfig):
        self.mkdocs = mkdocs

    def validate_options(self, options: dict) -> dict:
        """
        Validates generator options.
        The result is used as `options` parameter for `generate()` method.

        Args:
            options (dict): Raw options from markdown

        Returns:
            dict: Validated options
        """
        return self.options_schema.validate(options)

    @abstractmethod
    def generate(
        self, filepath: Path, symbol: Optional[str], options: dict
    ) -> Iterable["markdown_block"]:
        """
        Reads the source code and generates markdown blocks.

        Args:
            filepath (Path): Path to the source code
            symbol (Optional[str]): Symbol name
            options (dict): Generator options. See also `validate_options()`.

        Returns:
            Iterable["markdown_block"]: Markdown blocks
        """
        pass


class markdown_block:
    """
    Represents markdown blocks.
    """

    def __init__(self):
        self.lines = [""]

    def write(self, text: str):
        """
        Appends text to the last input.

        Args:
            text (str): Appended text
        """
        self.lines[-1] += text

    def writeln(self, line: str):
        """
        Appends text to the last input and insert line break.

        Args:
            line (str): Appended line
        """
        self.write(line)
        self.lines.append("")

    def build(self):
        """
        Builds final markdown block.

        Returns:
            str: Markdown block contents
        """
        return "\n".join(self.lines).strip("\r\n")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass


class markdown_heading(markdown_block):
    """
    Represents markdown heading block.
    """

    def __init__(self, text: Optional[str], level: int = 1):
        super().__init__()

        if text is None:
            text = ""

        self.writeln(("#" * level) + " " + text)


class markdown_paragraph(markdown_block):
    """
    Represents markdown paragraph block.
    """

    def __init__(self, text: Optional[str]):
        super().__init__()

        if text is None:
            text = ""

        self.writeln(text)
