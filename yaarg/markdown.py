from typing import MutableSequence
from xml.etree.ElementTree import Element

from markdown.blockprocessors import BlockProcessor
from markdown.core import Markdown
from markdown.extensions import Extension

PRIORITY = 75  # Right before markdown.blockprocessors.HashHeaderProcessor
NAME = "yaarg"


class YaargExtension(Extension):
    def extendMarkdown(self, md: Markdown):
        md.parser.blockprocessors.register(
            YaargBlockProcessor(md.parser), NAME, priority=PRIORITY
        )


class YaargBlockProcessor(BlockProcessor):
    def test(self, parent: Element, block: str):
        return False

    def run(self, parent: Element, blocks: MutableSequence[str]):
        pass
