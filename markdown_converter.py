import json
from typing import Dict
from dataclasses import dataclass


class ValidationException(Exception):
    def __init__(self, *args):
        self.message = None
        if args:
            self.message = args[0]

    def __str__(self):
        if self.message:
            return f'ValidationException: {self.message}'
        else:
            return f'ValidationException has been raised'


@dataclass
class TypesEnum:
    """
    Only for inheritance.
    Allows you to create classes similar to a 'dataclass' and
    get aggregated information about class members
    """

    # Additional members enumeration
    additional_list_of_types = []

    def additional_function_count_members(self) -> int:
        """
        Returns the count of all member fields.
        """

        # Its count all public names, except extra names
        #   (functions, values that are not dict keys etc.)
        return len(self.additional_function_get_members())

    def additional_function_get_members(self) -> list:
        """
        Return read-only list of values contained by types members
        """

        if not self.additional_list_of_types:
            # Its collect all public names, except extra names
            #   (functions, values that are not dict keys etc.)
            custom_prefix = "additional"
            self.additional_list_of_types = [
                self.__class__.__dict__[attr] for attr in self.__dir__() if (
                        not attr.startswith('__') and
                        not attr.startswith(custom_prefix)
                )
            ]
        return self.additional_list_of_types


class FieldTypesEnum(TypesEnum):
    # TODO: translate
    """
    Класс описывающий всевозможные ключи словарей-записей исходного json-документа.

    Внимание! Если класс будет расширен какими-то функциями,
    либо членами, не являющимися ключом словаря-записи,
    необходимо при названии их дописывать префикс additional!
    """
    type = "type"
    content = "content"


class ContentTypesEnum(TypesEnum):
    # TODO: translate
    """
    Класс описывающий всевозможные типы записей из исходного json-документа.

    Внимание! Если класс будет расширен какими-то функциями,
    либо членами, не являющимися ключом словаря-записи,
    необходимо при названии их дописывать префикс additional!
    """
    text = 'Text'
    title = 'Title'
    list = 'List'
    image = 'image'


FIELD_TYPES = FieldTypesEnum()
CONTENT_TYPES = ContentTypesEnum()


def validate_content(to_validate: Dict) -> None:
    # TODO: translate
    """
    Raises ValidationException error if to_validate item has unexpected structure,
    does nothing otherwise.
    """
    expected_fields_names = FIELD_TYPES.additional_function_get_members()
    expected_fields_count = FIELD_TYPES.additional_function_count_members()
    expected_fields_value_types = [str, ]

    try:
        assert len(to_validate.keys()) == expected_fields_count
    except AssertionError:
        raise ValidationException(f"Too many fields in passed collection for validation! "
                                  f"Got {len(to_validate.keys())} fields: {to_validate.keys()}, "
                                  f"expected {expected_fields_count}")

    for field, value in to_validate.items():
        try:
            assert field in expected_fields_names
        except AssertionError:
            raise ValidationException(f"Unexpected field's name {field}. "
                                      f"Here is the list of allowed names: {expected_fields_names}")

        try:
            assert type(value) in expected_fields_value_types
        except AssertionError:
            raise ValidationException(f"Unexpected field's value type {type(value)}. "
                                      f"Here is the list of allowed types: {expected_fields_value_types}")


class Converter:
    def __init__(self):
        self.markup_patterns = {
            CONTENT_TYPES.text: "{}",
            CONTENT_TYPES.title: "# {}",
            CONTENT_TYPES.list: "- {}",
            CONTENT_TYPES.image: "![]({})",
        }

        self.markdown_list_separator = '\n\n'
        self.markdown_list_line_break = ' ' * 2     # double space in the EOL for line-break

        self.markdown_new_line = '\n\n'

    def convert(self, value_type: str, value: str) -> str:
        after_conversion = ""

        match value_type:
            case CONTENT_TYPES.title:
                # h1 header using
                after_conversion = \
                    self.markup_patterns[CONTENT_TYPES.title].format(value)
            case CONTENT_TYPES.text:
                value = self._correct_line(value)
                after_conversion = self.markup_patterns[CONTENT_TYPES.text].format(value)
            case CONTENT_TYPES.list:
                list_items = [value for value in
                              value.split(self.markdown_list_separator) if value]
                for i in range(len(list_items)):
                    one_list_item = list_items[i]
                    correct_version = self._correct_line(one_list_item)
                    correct_version = correct_version.replace('\n', self.markdown_list_line_break + '\n')
                    list_items[i] = self.markup_patterns[CONTENT_TYPES.list].format(correct_version)

                after_conversion = self.markdown_new_line.join(list_items)
                after_conversion += self.markdown_new_line
            case CONTENT_TYPES.image:
                after_conversion = \
                    self.markup_patterns[CONTENT_TYPES.image].format(value)

        after_conversion += self.markdown_new_line
        return after_conversion

    def _correct_line(self, source_line) -> str:
        # todo: обрабатывать html-like стиль верстки (но там сложно, надо проверять много лексем)

        source_word_by_char = [x for x in source_line]

        # todo: построить автомат для простого случая лексем

        # вроде так как строка неизменяема,
        # то добавление 1 символа к строке создаст полную копию,
        # то есть имеет смысл создать список с буквами и работать со списком

        return source_line


if __name__ == "__main__":
    converter = Converter()
    # todo: opened all files from directory or getting file name
    with open("./source_json/data.json", 'r') as src:
        with open("./test.md", 'w') as dst:
            source_content = json.load(src)
            for item in source_content:
                validate_content(item)
                conversion_result = converter.convert(
                    item[FIELD_TYPES.type],
                    item[FIELD_TYPES.content])
                dst.write(conversion_result)

