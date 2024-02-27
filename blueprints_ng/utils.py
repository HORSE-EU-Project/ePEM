import inspect
from pathlib import Path
from typing import Any, Optional, Union, List, Text

from ruamel.yaml import YAML, StringIO


def rel_path(file: str) -> Path:
    mod_path = Path(inspect.stack()[1].filename).parent
    return Path(mod_path, file)


class MyYAML(YAML):
    """
    Custom override of the YAML class to allow the dump method to return a string instead of writing to file
    """

    def __init__(self: Any, *, typ: Optional[Union[List[Text], Text]] = None, pure: Any = False, output: Any = None, plug_ins: Any = None) -> None:
        super().__init__(typ=typ, pure=pure, output=output, plug_ins=plug_ins)
        self.preserve_quotes = True

    def dump(self, data, stream=None, **kw):
        """
        This override allow to return a string if no stream is provided
        Args:
            data: Data to serialize in yaml
            stream: Output stream for the serialized data
            **kw:

        Returns: YAML string if no stream is provided
        """
        inefficient = False
        if stream is None:
            inefficient = True
            stream = StringIO()
        YAML.dump(self, data, stream, **kw)
        if inefficient:
            return stream.getvalue()


yaml = MyYAML()
yaml_jinja = MyYAML(typ='jinja2')


def get_yaml_parser() -> MyYAML:
    return yaml


def get_yaml_parser_jinja2() -> MyYAML:
    return yaml_jinja
