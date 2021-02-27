from mkdocs.config import Config
from mkdocs.plugins import BasePlugin

from yaarg.markdown import YaargExtension


class YaargPlugin(BasePlugin):
    def on_config(self, config: Config, **kwargs) -> Config:
        config["markdown_extensions"].append(YaargExtension())
        return config
