# TODO: -done- обрабатывать ошибку когда пути к файлам не были переданы,
#       выбор json->md или json->html,
#       обработать случай когда более 4 пробелов - интерпретируется как
#           \t и делается особое форматирование (не имеет смысла, надо как-то обрабатывать),
#       добавить поддержку лидирующих пробелов в строке (в md они скипаются),
#       ловить ошибки и выводить текстом их содержимое, не пробрасывая наружу

import re
import os
import json
import click
import markdown

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
        #########################
        # For Markdown converting
        #########################

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

        #####################
        # For HTML converting
        #####################
        self.html_header_prefix = "header"
        self.html_id_generator = self._html_headers_id_generator()

    def convert_to_markdown(self, text_type: str, text: str) -> str:
        if text_type == CONTENT_TYPES.title:
            # h1 header using
            after_conversion = \
                self.markup_patterns[CONTENT_TYPES.title].format(text)
        elif text_type == CONTENT_TYPES.text:
            correct_version = self._correct_line_according_markdown_syntax(text)
            # Make line breaks according to the markup
            correct_version = correct_version.replace('\n', self.md_line_break + '\n')
            after_conversion = self.markup_patterns[CONTENT_TYPES.text].format(correct_version)
        elif text_type == CONTENT_TYPES.list:
            # Attention!
            # Symbols denoting a new line may change and depend on the operation of the ML service
            list_items = [value for value in
                          text.split(self.md_list_separator) if value]
            for i in range(len(list_items)):
                one_list_item = list_items[i]
                correct_version = self._correct_line_according_markdown_syntax(one_list_item)
                # Make line breaks according to the markup
                correct_version = correct_version.replace('\n', self.md_line_break + '\n')
                list_items[i] = self.markup_patterns[CONTENT_TYPES.list].format(correct_version)

            after_conversion = self.md_new_line.join(list_items)
            after_conversion += self.md_new_line
        elif text_type == CONTENT_TYPES.image:
            after_conversion = \
                self.markup_patterns[CONTENT_TYPES.image].format(text)
        else:
            raise RuntimeError(f"Unexpected type {text_type}! "
                               f"Possible values: {CONTENT_TYPES.additional_function_get_members()}")

        after_conversion += self.md_new_line
        return after_conversion

    def convert_to_html(self, text_type: str, text: str):
        # todo: draft
        md_repr = self.convert_to_markdown(text_type, text)
        after_html_converting = markdown.markdown(md_repr)

        if text_type == CONTENT_TYPES.title:
            header_pattern = r"<h1>"

            # set unique id
            after_html_converting = re.sub(header_pattern,
                                           r'<h1 id="{}">'.format(next(self.html_id_generator)),
                                           after_html_converting)

        return after_html_converting

    def _html_headers_id_generator(self):
        id_value = 0
        while True:
            yield self.html_header_prefix + str(id_value)
            id_value += 1

    def _correct_line_according_markdown_syntax(self, source_str) -> str:
        """
        Escaping text that is to be converted and may contain special characters and Markdown constructs.
        More about Markdown syntax in https://daringfireball.net/projects/markdown/syntax.text.
        """

        def escape_md_single_special_characters(to_correct: str) -> str:
            """
            Convert self.md_special_symbols to one string "...<symbols>..."
            Make with it md one_char_pattern "[...<symbols>...]" and remember detected occurrence with ().
            Every special symbol must be concatenated with '\' symbol for escaping
            Be careful with '\', '\\' and raw Python string in this code!
            """
            single_character_pattern = ''.join(['\\' + char for char in self.md_special_symbols])
            assert single_character_pattern

            one_char_pattern = r"([{}])".format(single_character_pattern)
            return re.sub(one_char_pattern, r"\\\1", to_correct)

        def escape_md_headers(to_correct: str) -> str:
            """
            Escape sequences like:
              #...# Heading
            """
            invisible_unicode_character = r"&#8291;"
            return re.sub(r"[^\n]( *)(#+)( +)", fr"\1{invisible_unicode_character}\2\3", to_correct)

        def escape_md_list_special_sequences(to_correct: str) -> str:
            """
            Md list-like sequences escaping

            For example ordered lists:
            1. First item.
            0. Second item.
            9. Third item.
            """
            # find <spaces><number><dot><spaces>
            invisible_unicode_character = r"&#8291;"
            return re.sub(r"( *)([0-9]+\.)( +)", fr"\1{invisible_unicode_character}\2\3", to_correct)

        def escape_html_like_sequences(to_correct: str) -> str:
            """
            If there are sections similar to html code,
            which is specially processed by the Markdown parser
            """
            markdown_left_angle_bracket_escape_sequence = r"&lt;"
            return re.sub(r"<", markdown_left_angle_bracket_escape_sequence, to_correct)

        def escape_all_types_of_braces(to_correct: str) -> str:
            """
            Helps to escape all special Markdown sequences with any types of braces.
            For example:
                - links:  [mysite](http://some_site.some.url/)
                - inline image syntax: ![mysite logo](http://some_site/favicon.png/ "optional title")
            """

            # Leading back-slash because pure braces are metacharacters in regular expressions
            unicode_codes = {
                r'\{': 123, r'\}': 125, r'\[': 91, r'\]': 93, r'\(': 40, r'\)': 41
            }

            for brace, unicode_number in unicode_codes.items():
                special_unicode_character = fr"&#{unicode_number};"
                to_correct = re.sub(fr"{brace}", special_unicode_character, to_correct)

            return to_correct

        source_str = escape_md_single_special_characters(source_str)
        source_str = escape_md_headers(source_str)
        source_str = escape_md_list_special_sequences(source_str)
        source_str = escape_html_like_sequences(source_str)
        source_str = escape_all_types_of_braces(source_str)

        return source_str


@click.command()
@click.option('--source', '-s', help="Path to the source file directory")
@click.option('--destination', '-d', help="Path to the output file. "
                                          "It will be created if not exist such file in existing directory")
def main(source: str = None, destination: str = None) -> None:
    def get_file_extension(file_path: str) -> str:
        return file_path.split('.')[-1]

    def check_paths_existing(source_file_path: str, destination_file_path: str) -> None:
        """
        Check if all paths passed
        """
        if not all([source_file_path, destination_file_path]):
            raise RuntimeError("Not enough files paths!")

    def check_paths_correctness(source_file_path: str, destination_file_path: str) -> None:
        """
        Check if files existing and source file has correct extension
        """
        if not os.path.isfile(source_file_path):
            raise RuntimeError(f"File with path '{source_file_path}' is not exist!")

        source_file_extension = get_file_extension(source_file_path)
        if source_file_extension != 'json':
            raise RuntimeError(f"Unexpected extension of source file: '{source_file_extension}'. "
                               f"Supported: json")

        # Check if destination file can be opened or create
        try:
            with open(destination_file_path, 'a'):
                pass
        except FileNotFoundError:
            raise RuntimeError(f"No such directory: '{destination_file_path}'.")

    def check_destination_path_extension(file_path: str) -> None:
        required_extensions = ('md', 'html')
        file_extension = get_file_extension(file_path)
        if file_extension not in required_extensions:
            raise RuntimeError(f"Unexpected extension: '{file_extension}'. Required: {required_extensions}.")

    # def get_id_with_increment() -> str:
    #     # todo: create endless generator
    #     nonlocal cur_header_id_num, header_id_prefix
    #
    #     res = header_id_prefix + str(cur_header_id_num)
    #     cur_header_id_num += 1
    #     return res

    #############################################
    # Verifying
    check_paths_existing(source, destination)
    check_paths_correctness(source, destination)
    check_destination_path_extension(destination)
    #############################################

    converter = Converter()
    # TODO: converting mode depends on destination file extension
    converting_extension = get_file_extension(destination)

    if converting_extension == 'html':
        converting_function = converter.convert_to_html
    else:
        # converting_extension == md
        converting_function = converter.convert_to_markdown

    with open(source, 'r') as src, open(destination, 'w') as dst:
        source_content = json.load(src)
        for item in source_content:
            validate_content(item)
            conversion_result = converting_function(
                item[FIELD_TYPES.type],
                item[FIELD_TYPES.content]
            )
            dst.write(conversion_result)

    #######################################33
    # cur_header_id_num = 0
    # header_id_prefix = "header"
    #
    # with open(source, 'r') as src:
    #     with open(destination, 'w') as dst:
    #         source_content = json.load(src)
    #         md_representation = []
    #
    #         # json (source) -> md
    #         for item in source_content:
    #             validate_content(item)
    #             conversion_result = converter.convert_to_markdown(
    #                 item[FIELD_TYPES.type],
    #                 item[FIELD_TYPES.content])
    #             md_representation.append(conversion_result)
    #
    #         # md -> html (destination)
    #         text = ''.join(md_representation)
    #
    #         # todo: delete
    #         #####################################
    #         with open("/home/ilya/WorkSpace/Projects/json-to-html/test.md", 'w') as md:
    #             md.write(text)
    #         #####################################
    #
    #         html_representation = markdown.markdown(text)
    #
    #         # Insert id to headers
    #         header_pattern = r"<h1>"
    #         html = re.sub(header_pattern,
    #                       lambda exp: r'<h1 id="{}">'.format(get_id_with_increment()),
    #                       html_representation)
    #
    #         dst.write(html)


if __name__ == "__main__":
    main()
