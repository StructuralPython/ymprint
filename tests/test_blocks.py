from ymprint.blocks import retrieve_block_variables
from ymprint.exceptions import YMPrintSyntaxException
import pytest

def test_retrieve_block_variables():

    var_bank = {"var_data": 1, "var_data_2": 3.24, "var_data_3": ("Python", "Tuple")}

    good_data = {
        "title": [
            "Paragraph text",
            {
                "_block": "$var_data"
            },
            {
                "_otherblock": {
                    "param": "$var_data_2"
                }
            },
            {
                "_thirdblock": [
                    "some text", "$var_data_3"
                ]
            }
        ]
    }

    assert retrieve_block_variables(good_data, {"vars": var_bank}) == {
        "title": [
            "Paragraph text",
            {
                "_block": 1
            },
            {
                "_otherblock": {
                    "param": 3.24
                }
            },
            {
                "_thirdblock": [
                    "some text", ("Python", "Tuple")
                ]
            }
        ]
    }