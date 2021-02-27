from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from schema import Schema


class BaseGenerator(ABC):
    name: str
    options_schema = Schema({})

    def get_name(self):
        if not hasattr(self, "name"):
            raise NotImplementedError()
        return self.name

    def validate_options(self, options: dict) -> dict:
        """Validates generator options.
        The result is used as `options` parameter for `generate()` method.

        Args:
            options (dict): Raw options from markdown.

        Returns:
            dict: Validated options.
        """
        return self.options_schema.validate(options)

    @abstractmethod
    def generate(self, filepath: Path, symbol: Optional[str], options: dict) -> str:
        """Reads the source code and generate markdown contents

        Args:
            filepath (Path): Path to the source code
            symbol (Optional[str]): Symbol name
            options (dict): Options

        Returns:
            str: Markdown contents
        """
        pass
