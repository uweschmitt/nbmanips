import copy

from nbmanips.cell import Cell
from nbmanips.selector import Selector


class NotebookBase:
    def __init__(self, content, name=None):
        self._nb = copy.deepcopy(content)
        self.name = name

    def __add__(self, other: 'NotebookBase'):
        # Copying the notebook
        nb = copy.deepcopy(self._nb)

        # Concatenating the notebooks
        nb['cells'] = nb['cells'] + other._nb['cells']
        return self.__class__(nb)

    def __getitem__(self, item):
        return self._nb[item]

    def __setitem__(self, item, value):
        self._nb[item] = value

    def __len__(self):
        if self._nb is None or 'cells' not in self._nb:
            return 0
        return len(self._nb['cells'])

    def __repr__(self):
        if self.name:
            return f'<Notebook "{self.name}">'
        else:
            return "<Notebook>"

    def __str__(self):
        return '\n'.join(str(Cell(cell, i, self._nb)) for i, cell in enumerate(self.cells))

    def iter_cells(self, selector=None, *args, **kwargs):
        return Selector(selector, *args, **kwargs).iter_cells(self._nb)

    def iter_neg_cells(self, selector, *args, **kwargs):
        return Selector(selector, *args, **kwargs).iter_cells(self._nb, neg=True)

    @property
    def cells(self):
        return self._nb['cells']
