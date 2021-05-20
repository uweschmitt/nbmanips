import pytest

from nbmanips import Notebook


@pytest.fixture(scope='function')
def nb0():
    return Notebook.read_ipynb('test_files/nb1.ipynb')


@pytest.fixture(scope='session')
def nb1():
    return Notebook.read_ipynb('test_files/nb1.ipynb')


@pytest.fixture(scope='session')
def nb2():
    return Notebook.read_ipynb('test_files/nb2.ipynb')


def test_read(nb1):
    assert len(nb1.nb['cells']) == 4


def test_name(nb1):
    assert nb1.name == 'nb1'


def test_len_empty():
    assert len(Notebook({})) == 0


def test_len(nb2):
    assert len(nb2) == 5


@pytest.mark.parametrize("search_term,case,expected", [
    ('b', False, None),
    ('Hello', False, 1),
    ('hello', False, 1),
    ('hello', True, None),
    ('a', True, 0),
    ('a ', True, 2),
])
def test_search(nb1, search_term, case, expected):
    # TODO: Test regexes
    # TODO: Test output
    assert nb1.search(search_term, case=case) == expected


@pytest.mark.parametrize("search_term,case,expected", [
    ('b', False, []),
    ('Hello', False, [1]),
    ('hello', False, [1]),
    ('hello', True, []),
    ('a', True, [0, 2, 3]),
    ('a ', True, [2]),
])
def test_search_all(nb1, search_term, case, expected):
    assert nb1.search_all(search_term, case=case) == expected


@pytest.mark.parametrize("old, new, case, first, expected_old, expected_new", [
    ('jupyter', 'Test', True, False, [], []),
    ('Hello', 'Test', True, False, [], [1]),
    ('hello', 'Test', True, False, [], []),
    ('a', 'Test', True, False, [], [0, 2, 3]),
    ('a', 'Test', True, True, [2, 3], [0]),
])
def test_replace(nb0, old, new, case, first, expected_old, expected_new):
    nb0.replace(old, new, first=first, case=case)
    assert nb0.search_all(old, case=case) == expected_old
    assert nb0.search_all(new, case=True) == expected_new


@pytest.mark.parametrize("selector, selector_kwargs, search_term, expected", [
    ('contains', {'text': 'Hello'}, 'World', []),
    ('contains', {'text': 'Hllo'}, 'World', [1]),
    ('contains', {'text': 'a '}, 'a', [0, 3]),
])
def test_erase(nb0, selector, selector_kwargs, search_term, expected):
    nb0.erase(selector, **selector_kwargs)
    assert nb0.search_all(search_term, case=True) == expected
    assert len(nb0) == 4


@pytest.mark.parametrize("selector, selector_kwargs, search_term, expected, expected_length", [
    ('contains', {'text': 'Hello'}, 'World', [], 3),
    ('contains', {'text': 'Hllo'}, 'World', [1], 4),
    ('contains', {'text': 'a '}, 'a', [0, 2], 3),
])
def test_delete(nb0, selector, selector_kwargs, search_term, expected, expected_length):
    nb0.delete(selector, **selector_kwargs)
    assert nb0.search_all(search_term, case=True) == expected
    assert len(nb0) == expected_length


@pytest.mark.parametrize("selector, selector_kwargs, search_term, expected, expected_length", [
    ('contains', {'text': 'Hello'}, 'World', [0], 1),
    ('contains', {'text': 'Hllo'}, 'World', [], 0),
    ('contains', {'text': 'a'}, 'a', [0, 1, 2], 3),
    ('contains', {'text': 'a '}, 'a', [0], 1),
])
def test_keep(nb0, selector, selector_kwargs, search_term, expected, expected_length):
    nb0.keep(selector, **selector_kwargs)
    assert nb0.search_all(search_term, case=True) == expected
    assert len(nb0) == expected_length


# def test_selectors(nb0, selector, selector_kwargs):
#     assert False
# def test_get_item(nb1):
#     assert nb1['cells'] == nb1.nb['cells']
#
# def test_tag(self, tag_key, tag_value, selector, *args, **kwargs):
#     ...
#
# def to_ipynb(self, path):
#     write_ipynb(self.nb, path)
