from typing import Optional, Union

from nbmanips.cell_utils import ParserBase
from nbmanips.cell_utils import TextParser
from nbmanips.cell_utils import HtmlParser
from nbmanips.cell_utils import ImageParser
from nbmanips.utils import total_size


def _get_output_types(output_type: Union[set, str]) -> set:
    if isinstance(output_type, str):
        if '/' in output_type:
            return {output_type, output_type.split('/')[0]}
        return {output_type}

    output_types = set()
    for output in output_type:
        output_types |= _get_output_types(output)
    return output_types


class CellOutput:
    output_type = None
    _output_types = {}
    _parsers = {}

    def __init__(self, content):
        self.content = content

    @property
    def output_types(self) -> set:
        raise NotImplementedError()

    def to_str(self, *args, **kwargs):
        return ''

    def erase_output(self, output_types: set):
        raise NotImplementedError()

    def has_output_type(self, output_types: set):
        """
        Select cells that have a given output_type

        :param output_types: Output Types(MIME types) to select: text/plain, text/html, image/png, ...
        :type output_types: set
        :return: a bool object (True if cell should be selected)
        """
        return output_types & self.output_types

    def byte_size(self, output_types: Optional[set]):
        if output_types is None or self.has_output_type(output_types):
            return total_size(self.content)
        return 0

    @classmethod
    def register_parser(cls, output_type, parser: ParserBase):
        cls._parsers[output_type] = parser

    @property
    def default_parsers(self):
        return {key for key, value in self._parsers.items() if value.default_state}

    def __new__(cls, content, *args, **kwargs):
        output_type = content['output_type']
        output_class = cls._output_types[output_type]
        obj = super().__new__(output_class)
        output_class.__init__(obj, content, *args, **kwargs)
        return obj

    def __init_subclass__(cls, output_type=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if output_type:
            cls._output_types[output_type] = cls
        cls.output_type = output_type


class StreamOutput(CellOutput, output_type='stream'):
    @property
    def text(self):
        return self.content['text']

    @property
    def output_types(self):
        return _get_output_types('text/plain')

    def to_str(self, *args, **kwargs):
        output_text = self.text
        if not isinstance(output_text, str):
            output_text = '\n'.join(output_text)
        return output_text

    def erase_output(self, output_types: set):
        return None if self.has_output_type(output_types) else self.content


class DataOutput(CellOutput):
    default_data_types = ['image/png', 'text/html', 'text/plain']

    def to_str(self, parsers=None, parsers_config=None, excluded_data_types=None):
        parsers = self.default_parsers if parsers is None else set(parsers)
        parsers_config = parsers_config or {}
        exclude_data_types = {} if excluded_data_types is None else set(excluded_data_types)

        data = self.content['data']
        data_types = [dt for dt in self.default_data_types if dt in parsers] + list(data)
        for data_type in data_types:
            if data_type in exclude_data_types or data_type not in data:
                continue

            output_text = data[data_type]
            if not isinstance(output_text, str):
                output_text = '\n'.join(output_text)

            if data_type in parsers and data_type in self._parsers:
                parser = self._parsers[data_type]
                output_text = parser.parse(output_text, **parsers_config.get(data_type, {}))
            return output_text

    def erase_output(self, output_types: set):
        for key in output_types:
            self.content['data'].pop(key, None)

        if not self.content['data']:
            return None

        return self.content

    @property
    def output_types(self):
        return _get_output_types(self.content['data'])

    def has_output_type(self, output_types: set):
        return output_types & self.output_types

    def byte_size(self, output_types: Optional[set]):
        if output_types is None:
            return total_size(self.content)
        elif not self.has_output_type(output_types):
            return 0
        else:
            return total_size({key: value for key, value in self.content['data'].items() if key in output_types})


class ErrorOutput(CellOutput, output_type='error'):
    @property
    def ename(self):
        return self.content['ename']

    @property
    def evalue(self):
        return self.content['evalue']

    @property
    def traceback(self):
        return self.content['traceback']

    @property
    def output_types(self):
        return _get_output_types('text/error')

    def to_str(self, *args, **kwargs):
        return '\n'.join(self.traceback + [f"{self.ename}: {self.evalue}"])

    def erase_output(self, output_types: set):
        return None if self.has_output_type(output_types) else self.content


class DisplayData(DataOutput, output_type='display_data'):
    pass


class ExecuteResult(DataOutput, output_type='execute_result'):
    @property
    def execution_count(self):
        return self.content.get("execution_count", None)


CellOutput.register_parser('text/plain', TextParser())
CellOutput.register_parser('text/html', HtmlParser())
CellOutput.register_parser('image/png', ImageParser())
