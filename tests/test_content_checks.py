from ymprint import content_checks as con


def test_check_for_subelements():
    # Passes as subheading
    subs1 = {
        "heading": [
            "paragraph text",
            {"subheading": "paragraph text 2"}
        ]
    }
    subs2 = {
        "heading": [
            "paragraph text",
            "bullet",
            "bullet"
        ]
    }
    subs3 = {
        "heading": [
            "paragraph text",
            "bullet",
            ['subarray', 'subarray2']
        ]
    }
    # Passes as subheading
    subs4 = {
        "heading": [
            {"subheading": "paragraph text"}
        ]
    }
    # Passes as subheading
    subs5 = {
        "heading": [
            {"subheading": "paragraph text"},
            "paragraph text",
            "second paragraph"
        ]
    }
    assert con.check_for_subelements(subs1['heading'], context={})
    assert not con.check_for_subelements(subs2['heading'], context={})
    assert not con.check_for_subelements(subs3['heading'], context={})
    assert not con.check_for_subelements(subs4['heading'], context={})
    assert con.check_for_subelements(subs5['heading'], context={})


def test_check_for_tables():
    subs1 = {
        "heading": [
            "paragraph text",
            {"subheading": "paragraph text 2"}
        ]
    }
    subs2 = {
        "heading": [
            "paragraph text",
            "bullet",
            "bullet"
        ]
    }
    subs3 = {
        "heading": [
            "paragraph text",
            "bullet",
            ['subarray', 'subarray2']
        ]
    }
    subs4 = {
        "heading": [
            {"subheading": "paragraph text"},
            {"subtitle": "text"}
        ]
    }
    subs5 = {
        "heading": [
            {"subheading": "paragraph text"},
            "paragraph text",
            "second paragraph"
        ]
    }
    subs6 = {
        "heading": [
            {"subheading": "paragraph text"},
            {"subtitle": "text"},
            {"one col": "valu", "two col": "value", "three col": "value"}
        ]
    }
    assert not con.check_for_tables(subs1['heading'], context={})
    assert not con.check_for_tables(subs2['heading'], context={})
    assert not con.check_for_tables(subs3['heading'], context={})
    assert not con.check_for_tables(subs4['heading'], context={})
    assert not con.check_for_tables(subs4, context={})

    assert not con.check_for_tables(subs5['heading'], context={})
    assert not con.check_for_tables(subs6['heading'], context={})


def test_check_for_bullets():
    subs1 = {
        "heading": [
            "paragraph text",
            {"subheading": "paragraph text 2"}
        ]
    }
    subs2 = {
        "heading": [
            "paragraph text",
            "bullet",
            "bullet"
        ]
    }
    subs3 = {
        "heading": [
            "paragraph text",
            "bullet",
            ['subarray', 'subarray2']
        ]
    }
    subs4 = {
        "heading": [
            {"subheading": "paragraph text"}
        ]
    }
    subs5 = {
        "heading": [
            {"subheading": "paragraph text"},
            "paragraph text",
            "second paragraph"
        ]
    }
    assert not con.check_for_ul(subs1['heading'], context={})
    assert con.check_for_ul(subs2['heading'], context={})
    assert not con.check_for_ul(subs3['heading'], context={})
    assert not con.check_for_ul(subs4['heading'], context={})
    assert not con.check_for_ul(subs5['heading'], context={})


def test_check_for_numbered_list():
    subs1 = {
        "heading": [
            "paragraph text",
            {"subheading": "paragraph text 2"}
        ]
    }
    subs2 = {
        "heading": [
            "paragraph text",
            "bullet",
            "bullet"
        ]
    }
    subs3 = {
        "heading": {
            1: 'bullet 1',
            2: 'bullet 3', 
            3: 'bullet 4',
        }
    }
    subs4 = {
        "heading": {
            102: 'bullet 1',
            48: 'bullet 3', 
            2: 'bullet 4',
        }
    }
    assert not con.check_for_ol(subs1['heading'], context={})
    assert not con.check_for_ol(subs2['heading'], context={})
    assert con.check_for_ol(subs3['heading'], context={})
    assert con.check_for_ol(subs4['heading'], context={})


def test_check_for_ordered_nested_lists():
    subs3 = {
        "heading": {
            1: 'bullet 1',
            2: 'bullet 3', 
            3: 'bullet 4',
        }
    }
    subs4 = {
        "heading": {
            1: 'bullet 1',
            2: 'bullet 3', 
            3: 'bullet 4',
            4: {
                1: 'bullet 5',
                2: 'bullet 6',
                3: 'bullet 7',
                4: {
                    1: 'bullet 8',
                    2: 'bullet 9',
                    3: {
                        1: 'bullet 10',
                        2: 'bullet 11'
                    }
                }
            }
        }
    }
    subs5 = {
        "heading": {
            1: 'bullet 1',
            2: 'bullet 3', 
            3: 'bullet 4',
            4: {
                1: 'bullet 5',
                2: 'bullet 6',
                3: 'bullet 7',
                4: {
                    1: 'bullet 8',
                    2: 'bullet 9',
                    3: {
                        1: 'bullet 10',
                        2: ['elem', 'elem2']
                    }
                }
            }
        }
    }
    assert con.check_for_ordered_nested_lists(subs3['heading'], {})
    assert con.check_for_ordered_nested_lists(subs4['heading'], {})
    assert not con.check_for_ordered_nested_lists(subs5['heading'], {})



def test_check_for_nested_lists():
    subs6 = {
        "heading": [
            'bullet 1',
            [
                'sub bullet 2',
                'sub bullet 3',
                [
                    'sub bullet 4',
                    ['sub bullet 5']
                ]]
        ]
    }
    subs7 = {
        "heading": [
            'bullet 1',
            [
                'sub bullet 2',
                'sub bullet 3',
                [
                    {"sub heading": "topic"},
                    ['sub bullet 5']
                ]]
        ]
    }
    assert con.check_for_nested_lists(subs6['heading'], {})
    assert not con.check_for_nested_lists(subs7['heading'], {})

