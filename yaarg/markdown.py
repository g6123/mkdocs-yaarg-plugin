import re
from pathlib import Path
from typing import List

import yaml
from markdown.core import Markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from mkdocs.config.base import Config as MKDocsConfig

from yaarg.resolver import Resolver

PRIORITY = 26  # Before FencedBlockPreprocessor
NAME = "yaarg"


class YaargExtension(Extension):
    def __init__(self, resolver: Resolver, mkdocs: MKDocsConfig, **kwargs):
        super().__init__(**kwargs)
        self.resolver = resolver
        self.mkdocs = mkdocs

    def extendMarkdown(self, md: Markdown):
        preprocessor = YaargPreprocessor(md)
        preprocessor.resolver = self.resolver
        preprocessor.mkdocs = self.mkdocs
        md.preprocessors.register(preprocessor, NAME, priority=PRIORITY)


class YaargPreprocessor(Preprocessor):
    EOF = "\0"

    resolver: Resolver
    mkdocs: MKDocsConfig
    open_pattern = re.compile(r"^:::\s+(.+?)$")
    close_pattern = re.compile(r"^$")

    def run(self, lines: List[str]):
        cursor = 0
        marker = -1

        while cursor <= len(lines):
            try:
                line = lines[cursor]
            except IndexError:
                line = ""

            if marker >= 0:
                if re.match(self.close_pattern, line):
                    buffer = lines[marker:cursor]
                    lines = lines[:marker] + lines[cursor:]
                    cursor -= len(buffer)

                    buffer = self._process(buffer)
                    lines[marker + 1 : 0] = buffer
                    cursor += len(buffer)

                    marker = -1
            else:
                if re.match(self.open_pattern, line):
                    marker = cursor

            cursor += 1

        return lines

    def _process(self, lines: List[str]) -> List[str]:
        match = re.match(self.open_pattern, lines[0])
        if match is None:
            return []

        target = match.group(1).split(":", 2)
        if len(target) < 2:
            filename, symbol = target[0], None
        else:
            filename, symbol = target

        options = yaml.safe_load("\n".join(lines[1:]).strip())
        if not options:
            options = {}

        filepath = Path(self.mkdocs["config_file_path"]).parent / Path(filename)
        generator, options = self.resolver.resolve(filepath, options)

        blocks = generator.generate(filepath, symbol, options)
        chunk = "\n\n".join(blocks)
        return chunk.splitlines()
