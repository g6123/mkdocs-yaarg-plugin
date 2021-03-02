import os
import re
from collections import OrderedDict
from dataclasses import dataclass, replace
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Generator, Optional, Set, Type, cast

from docstring_parser import parse as parse_docstring
from docstring_parser.common import DocstringParam
from parso.grammar import load_grammar
from parso.python.tree import (
    Class,
    Function,
    Module,
    Name,
    Param,
    PythonNode,
    Scope,
    String,
)
from schema import Optional as OptionalItem, Schema

from .base import BaseGenerator, markdown_block, markdown_heading, markdown_paragraph

__all__ = ["ParsoGenerator"]


@dataclass
class ParsoGeneratorContext:
    basepath: Path
    filepath: Path
    symbol: Optional[str]
    parent: Optional[Scope]
    depth: int
    deep: bool
    options: Dict[str, Any]

    @property
    def parent_name(self):
        try:
            return self.parent.name.value
        except AttributeError:
            return None

    def set_parent(self, parent):
        return replace(self, parent=parent, depth=self.depth + 1)


class ParsoGenerator(BaseGenerator):
    name = "parso"
    options_schema = Schema(
        {
            OptionalItem("version", default=None): str,
            OptionalItem("encoding", default="utf-8"): str,
            OptionalItem("depth", default=2): int,
            OptionalItem("deep", default=True): bool,
            OptionalItem(
                "methods", default={"undocumented": True, "private": False}
            ): Schema(
                {
                    OptionalItem("undocumented", default=True): bool,
                    OptionalItem("private", default=False): bool,
                }
            ),
        }
    )

    def generate(self, filepath, symbol, options):
        grammar = load_grammar(version=options["version"])
        with open(filepath, encoding=options["encoding"]) as f:
            parser = grammar.parse(f.read())
            module: Module = parser.get_root_node()

        if symbol is not None:
            root_node = find_symbol(module, symbol)
        else:
            root_node = module

        context = ParsoGeneratorContext(
            basepath=Path(self.mkdocs["config_file_path"]).parent,
            filepath=filepath,
            symbol=symbol,
            parent=None,
            depth=options["depth"],
            deep=options["deep"],
            options=options,
        )
        return self._generate_doc(root_node, context)

    def _generate_doc(self, node: Scope, context: ParsoGeneratorContext):
        if isnode(node, Module):
            yield from self._generate_module_doc(cast(Module, node), context)
        elif isnode(node, Class):
            yield from self._generate_class_doc(cast(Class, node), context)
        elif isnode(node, Function):
            yield from self._generate_func_doc(cast(Function, node), context)

    def _generate_module_doc(self, module_node: Module, context: ParsoGeneratorContext):
        module_path = context.filepath.relative_to(context.basepath).parts
        if module_path[-1] == "__init__.py":
            module_path = module_path[:-1]
        else:
            module_name, _ = os.path.splitext(module_path[-1])
            module_path = module_path[:-1] + (module_name,)

        yield markdown_heading(
            "`{title}`".format(title=".".join(module_path)),
            level=context.depth,
        )

        doc_node = cast(Optional[String], module_node.get_doc_node())
        if doc_node:
            doc = parse_docstring(doc_node._get_payload())
            yield markdown_paragraph(doc.short_description)
            yield markdown_paragraph(doc.long_description)

        if context.deep:
            for child_node in iter_children(module_node):
                yield from self._generate_doc(
                    child_node, context.set_parent(module_node)
                )

    def _generate_class_doc(self, class_node: Class, context: ParsoGeneratorContext):
        yield markdown_heading(f"`{class_node.name.value}`", level=context.depth)

        doc_node = cast(Optional[String], class_node.get_doc_node())
        if doc_node:
            doc = parse_docstring(doc_node._get_payload())
            yield markdown_paragraph(doc.short_description)
            yield markdown_paragraph(doc.long_description)

        if context.deep:
            for child_node in iter_children(class_node):
                yield from self._generate_doc(
                    child_node, context.set_parent(class_node)
                )

    def _generate_func_doc(self, func_node: Function, context: ParsoGeneratorContext):
        is_undocumented = func_node.get_doc_node() is None
        is_private = re.match(r"^_[^_]+?$", func_node.name.value)

        if isnode(context.parent, Class):
            if not context.options["methods"]["undocumented"]:
                if is_undocumented:
                    return

            if not context.options["methods"]["private"]:
                if is_private:
                    return

            is_constructor = func_node.name.value == "__init__"
            is_static = any(
                re.search("(staticmethod|classmethod)", decorator_node.get_code())
                for decorator_node in func_node.get_decorators()
            )
            prefix = context.parent_name + ("." if is_static else "#")
        else:
            is_constructor = False
            is_static = True
            prefix = ""

        doc_node = cast(Optional[String], func_node.get_doc_node())
        if doc_node:
            doc = parse_docstring(doc_node._get_payload())
        else:
            doc = None

        param_nodes: OrderedDict[str, Param] = OrderedDict()
        for idx, param_node in enumerate(func_node.get_params()):
            param_name = param_node.name.value
            if idx == 0 and param_name in ("self", "cls"):
                continue
            param_nodes[param_name] = param_node

        param_docs: OrderedDict[str, DocstringParam] = OrderedDict()
        if doc:
            param_docs.update([(param.arg_name, param) for param in doc.params])

        param_string = (
            re.sub(
                r"(^\s+|\r?\n|\s+$)",
                "",
                "".join(param_node.get_code() for param_node in param_nodes.values()),
            )
            .rstrip(",")
            .strip()
        )

        yield markdown_heading(
            "`{prefix}{title}({params})`".format(
                prefix=prefix,
                title=func_node.name.value,
                params=param_string,
            ),
            level=context.depth,
        )

        if doc:
            yield markdown_paragraph(doc.short_description)

        if param_nodes or param_docs:
            yield markdown_heading("Arguments", level=context.depth + 1)
            with markdown_block() as block:
                block.writeln("| Name | Type | Description | Default |")
                block.writeln("| ---- | ---- | ----------- | ------- |")

                seen: Set[str] = set()
                for param_name in chain(param_docs, param_nodes):
                    if param_name in seen:
                        continue

                    seen.add(param_name)
                    param_node = param_nodes.get(param_name)
                    param_doc = param_docs.get(param_name)

                    block.writeln(
                        "| {name} | {type} | {description} | {default} |".format(
                            name=param_name,
                            type=(
                                getattr(param_doc, "type_name", None)
                                or get_code(getattr(param_node, "annotation", None))
                                or "-"
                            ),
                            description=getattr(param_doc, "description", "-"),
                            default=(
                                getattr(param_doc, "default", None)
                                or get_code(getattr(param_node, "default", None))
                                or "-"
                            ),
                        )
                    )

                yield block.build()

        if not is_constructor:
            yield markdown_heading("Returns", level=context.depth + 1)
            with markdown_block() as block:
                if doc:
                    returns_doc = doc.returns
                else:
                    returns_doc = None

                block.writeln("| Type | Description |")
                block.writeln("| ---- | ----------- |")
                block.writeln(
                    "| {type} | {description} |".format(
                        type=(
                            getattr(returns_doc, "type_name", None)
                            or get_code(func_node.annotation)
                            or "-"
                        ),
                        description=getattr(returns_doc, "description", None) or "-",
                    )
                )
                yield block.build()

        if doc and doc.long_description:
            yield markdown_heading("Details", level=context.depth + 1)
            yield markdown_paragraph(doc.long_description)


def find_symbol(module: Optional[Module], path: str) -> Optional[Scope]:
    current_node = cast(Optional[Scope], module)

    for part in path.split("."):
        child: Scope
        for child in iter_children(current_node):
            name: Optional[Name] = getattr(child, "name", None)
            if name is not None and name.value == part:
                current_node = child
                break
        else:
            return None

    return current_node


def iter_children(node: Optional[Scope]) -> Generator[Scope, None, None]:
    if node is None:
        return

    for child in node.children:
        if type(child) is PythonNode:
            yield from iter_children(child)
        else:
            yield child


def get_code(node: Optional[Scope]):
    if node is None:
        return None

    return node.get_code()


def isnode(node: Optional[Scope], node_cls: Type[Scope]):
    if node is None:
        return False

    return node.type == node_cls.type
