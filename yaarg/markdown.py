import re
from pathlib import Path
from typing import MutableSequence
from xml.etree.ElementTree import Element

import yaml
from markdown.blockparser import BlockParser
from markdown.blockprocessors import BlockProcessor
from markdown.core import Markdown
from markdown.extensions import Extension
from mkdocs.config.base import Config as MKDocsConfig

from yaarg.resolver import Resolver

PRIORITY = 75  # Right before markdown.blockprocessors.HashHeaderProcessor
NAME = "yaarg"


class YaargExtension(Extension):
    def __init__(self, resolver: Resolver, mkdocs: MKDocsConfig, **kwargs):
        super().__init__(**kwargs)
        self.resolver = resolver
        self.mkdocs = mkdocs

    def extendMarkdown(self, md: Markdown):
        md.parser.blockprocessors.register(
            YaargBlockProcessor(md.parser, self.resolver, self.mkdocs),
            NAME,
            priority=PRIORITY,
        )


class YaargBlockProcessor(BlockProcessor):
    PATTERN = re.compile(r"^:::\s+(.+?)$", re.MULTILINE)

    parser: BlockParser
    resolver: Resolver
    mkdocs: MKDocsConfig

    def __init__(self, parser: BlockParser, resolver: Resolver, mkdocs: MKDocsConfig):
        super().__init__(parser)
        self.resolver = resolver
        self.mkdocs = mkdocs

    def test(self, parent: Element, block: str):
        return re.search(self.PATTERN, block) is not None

    def run(self, parent: Element, blocks: MutableSequence[str]):
        source_block = blocks.pop(0)
        match = re.search(self.PATTERN, source_block)
        assert match is not None

        target = match.group(1).split(":", 2)
        if len(target) < 2:
            filename, symbol = target[0], None
        else:
            filename, symbol = target

        raw_options = yaml.safe_load(source_block[match.end(1) :].strip())
        if not raw_options:
            raw_options = {}

        filepath = Path(self.mkdocs["config_file_path"]).parent / Path(filename)

        generator = self.resolver.resolve(
            filepath,
            generator=raw_options.get("generator"),
            options=raw_options.get("resolver"),
        )
        options = generator.validate_options(raw_options)

        blocks[0:0] = [
            block.build() for block in generator.generate(filepath, symbol, options)
        ]
