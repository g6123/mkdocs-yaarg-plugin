from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Dict, Optional, Sequence, Type

from mkdocs.config import Config as MKDocsConfig

from yaarg.generators.base import BaseGenerator

__all__ = ["Resolver", "ResolverConfig", "ResolverError"]


@dataclass
class ResolverRule:
    glob: str
    generator: str
    options: dict


class ResolverError(Exception):
    pass


class Resolver:
    """
    Initializes an appropriate generator instance for the given filepath.
    """

    rules: Sequence[ResolverRule]
    generator_caches: Dict[str, BaseGenerator]

    def __init__(self, rules: Sequence[ResolverRule], mkdocs: MKDocsConfig):
        self.rules = rules
        self.mkdocs = mkdocs
        self.generator_caches = {}

    def resolve(
        self,
        filepath: Path,
        generator: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> BaseGenerator:
        if options is None:
            options = {}
        else:
            options = options.copy()

        if generator is None:
            for rule in self.rules:
                if self.match(rule, filepath, options):
                    generator = rule.generator
                    options.update(rule.options)
                    break
            else:
                raise ResolverError(filepath)

        if generator not in self.generator_caches:
            generator_cls: Type[BaseGenerator] = self.load(generator)
            self.generator_caches[generator] = generator_cls(self.mkdocs)

        return self.generator_caches[generator]

    def load(self, generator_path: str):
        module_name, obj_name = generator_path.rsplit(":", 1)
        module = import_module(module_name)
        try:
            return getattr(module, obj_name)
        except AttributeError:
            raise ImportError(generator_path)

    def match(self, rule: ResolverRule, filepath: Path, options: dict) -> bool:
        return filepath.match(rule.glob)
