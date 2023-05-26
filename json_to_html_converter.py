# TODO: обрабатывать ошибку когда пути к файлам не были переданы,
#       когда файлы не существуют,
#       выбор json->md или json->html,
#       обработать случай когда более 4 пробелов - интерпретируется как
#           \t и делается особое форматирование (не имеет смысла, надо как-то обрабатывать),
#       добавить поддержку лидирующих пробелов в строке (в md они скипаются)

import json
import re
import markdown
import click

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
    """
    A class that describes all possible keys of the dictionaries-records of the original json document.

    Attention! If the class is extended with some functions,
    or members that are not a dictionary entry key,
    it is necessary to add the prefix "additional" when naming them!
    """
    type = "type"
    content = "content"


class ContentTypesEnum(TypesEnum):
    """
    A class that describes all kinds of records from the original json document.

    Attention! If the class is extended with some functions,
    or members that are not a dictionary entry key,
    it is necessary to add the prefix additional when naming them!
    """
    text = 'Text'
    title = 'Title'
    list = 'List'
    image = 'image'


FIELD_TYPES = FieldTypesEnum()
CONTENT_TYPES = ContentTypesEnum()


def validate_content(to_validate: Dict) -> None:
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

        self.md_list_separator = '\n\n'
        self.md_line_break = ' ' * 2     # double space in the EOL for line-break

        self.md_new_line = '\n\n'

        # Warning! Character '\\' may be incorrect interpret in non Unix-like systems.
        # Attention! List of special characters:
        #   ['#', '*', '-', '+', '\\', '_', '{', '}', '[', ']', '(', ')', '#', '.', '!']
        # For some reason the local Markdown parser doesn't require escaping some characters.
        # Maybe it depends on the version of the Markdown processor.
        self.md_special_symbols = ['*', '-', '+']

    def convert_to_md(self, value_type: str, value: str) -> str:
        if value_type == CONTENT_TYPES.title:
            # h1 header using
            after_conversion = \
                self.markup_patterns[CONTENT_TYPES.title].format(value)
        elif value_type == CONTENT_TYPES.text:
            correct_version = self._correct_line(value)
            # Make line breaks according to the markup
            correct_version = correct_version.replace('\n', self.md_line_break + '\n')
            after_conversion = self.markup_patterns[CONTENT_TYPES.text].format(correct_version)
        elif value_type == CONTENT_TYPES.list:
            # Attention!
            # Symbols denoting a new line may change and depend on the operation of the ML service
            list_items = [value for value in
                          value.split(self.md_list_separator) if value]
            for i in range(len(list_items)):
                one_list_item = list_items[i]
                correct_version = self._correct_line(one_list_item)
                # Make line breaks according to the markup
                correct_version = correct_version.replace('\n', self.md_line_break + '\n')
                list_items[i] = self.markup_patterns[CONTENT_TYPES.list].format(correct_version)

            after_conversion = self.md_new_line.join(list_items)
            after_conversion += self.md_new_line
        elif value_type == CONTENT_TYPES.image:
            after_conversion = \
                self.markup_patterns[CONTENT_TYPES.image].format(value)
        else:
            raise RuntimeError(f"Unexpected type {value_type}! "
                               f"Possible values: {CONTENT_TYPES.additional_function_get_members()}")

        after_conversion += self.md_new_line
        return after_conversion

    def _correct_line(self, source_line) -> str:
        """
        Escaping text that is to be converted and may contain special characters and Markdown constructs
        """

        # TODO: 1) -done- всякие случаи с 2ми символами типа "1.", и тд (в основном для листов)
        #       2) -done- всякие варианты с #
        #       3) особые случаи со скобками (например ![Alt text](/path/to/img.jpg))
        #       4) посмотреть где каждая скобка используется в особых случаях
        #       Полный список
        #           List of special characters: ['#', '*', '-', '+', '\\', '_',
        #                                       '{', '}', '[', ']', '(', ')', '#', '.', '!']

        def escape_single_characters(to_correct: str) -> str:
            # Convert self.md_special_symbols to one string "...<symbols>..."
            # Make with it md one_char_pattern "[...<symbols>...]" and remember detected occurrence with ().
            # Every special symbol must be concatenated with '\' symbol for escaping
            # Be careful with '\', '\\' and raw Python string in this code!
            single_character_pattern = ''.join(['\\' + char for char in self.md_special_symbols])
            assert single_character_pattern

            one_char_pattern = r"([{}])".format(single_character_pattern)
            return re.sub(one_char_pattern, r"\\\1", to_correct)

        def escape_headers(to_correct: str) -> str:
            ########################
            # Escape sequences like:
            #   #...# Heading
            ########################
            invisible_character = r"&#8291;"
            return re.sub(r"[^\n]( *)(#+)( +)", fr"\1{invisible_character}\2\3", to_correct)

        def escape_list_special_sequences(to_correct: str) -> str:
            #################################
            # Md list-like sequences escaping
            #
            # For example ordered lists:
            # 1. First item.
            # 0. Second item.
            # 9. Third item.
            #
            #################################
            # find <spaces><number><dot><spaces>
            invisible_character = r"&#8291;"
            return re.sub(r"( *)([0-9]+\.)( +)", fr"\1{invisible_character}\2\3", to_correct)

        def escape_html_like_sequences(to_correct: str) -> str:
            #####################################################
            # If there are sections similar to html code,
            # which is specially processed by the Markdown parser
            #####################################################
            markdown_left_angle_bracket_escape_sequence = r"&lt;"
            return re.sub(r"<", markdown_left_angle_bracket_escape_sequence, to_correct)

        source_line = escape_single_characters(source_line)

        source_line = escape_headers(source_line)
        source_line = escape_list_special_sequences(source_line)

        source_line = escape_html_like_sequences(source_line)

        return source_line


@click.command()
@click.option('--source', '-s', help="Path to the source file directory")
@click.option('--destination', '-d', help="Path to the directory for the output file")
def main(source: str, destination: str) -> None:
    def get_id_with_increment() -> str:
        nonlocal cur_header_id_num, header_id_prefix

        res = header_id_prefix + str(cur_header_id_num)
        cur_header_id_num += 1
        return res

    cur_header_id_num = 0
    header_id_prefix = "header"

    converter = Converter()

    with open(source, 'r') as src:
        with open(destination, 'w') as dst:
            source_content = json.load(src)
            md_representation = []

            # json (source) -> md
            for item in source_content:
                validate_content(item)
                conversion_result = converter.convert_to_md(
                    item[FIELD_TYPES.type],
                    item[FIELD_TYPES.content])
                md_representation.append(conversion_result)

            # md -> html (destination)
            text = ''.join(md_representation)

            # todo: delete
            #####################################
            with open("/home/ilya/WorkSpace/Projects/json-to-html/test.md", 'w') as md:
                md.write(text)
            #####################################

            html_representation = markdown.markdown(text)

            # Insert id to headers
            header_pattern = r"<h1>"
            html = re.sub(header_pattern,
                          lambda exp: r'<h1 id="{}">'.format(get_id_with_increment()),
                          html_representation)

            dst.write(html)


if __name__ == "__main__":
    main()
