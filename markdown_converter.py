import json
from typing import Dict
from dataclasses import dataclass


@dataclass
class FieldTypes:
    type = "type"
    content = "content"


@dataclass
class ContentTypes:
    pass


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


def validate_content(to_validate: Dict) -> None:
    """
    Raises ValidationException error if to_validate item has unexpected structure,
    does nothing otherwise.
    """
    expected_fields_names = ["type", "content"]
    expected_fields_value_types = [str, ]
    expected_fields_count = len(expected_fields_names)

    try:
        assert len(to_validate.keys()) == expected_fields_count
    except AssertionError:
        raise ValidationException("Too many fields in passed collection for validation!")

    for field, value in to_validate.items():
        try:
            assert field in expected_fields_names
        except AssertionError:
            raise ValidationException(f"Unexpected field's name {field}")

        try:
            assert type(value) in expected_fields_value_types
        except AssertionError:
            raise ValidationException(f"Unexpected field's value type {type(value)}")


class Converter:
    def __init__(self):
        pass

    def convert(self, value_type, value: str) -> str:
        pass


if __name__ == "__main__":
    converter = Converter()
    # todo: opened all files from directory or getting file name
    with open("./source_json/data.json", 'r') as src:
        with open("./test.md", 'w') as dst:
            source_content = json.load(src)
            for item in source_content:
                validate_content(item)
                conversion_result = converter.convert(item['type'], item['content'])
                dst.write()

