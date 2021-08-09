import os
import json
from copy import deepcopy

try:
    import nbformat
except ImportError:
    nbformat = None

try:
    import nbconvert
except ImportError:
    nbconvert = None

from nbmanips.notebook_base import NotebookBase
from nbmanips.selector import is_new_slide, has_slide_type, has_output_type


class ClassicNotebook(NotebookBase):
    def tag(self, tag_key, tag_value):
        """
        Add metadata to the selected cells
        :param tag_key:
        :param tag_value:
        """
        for cell in self.iter_cells():
            value = deepcopy(tag_value)
            if tag_key in cell.cell['metadata'] and isinstance(cell.cell['metadata'][tag_key], dict):
                cell.metadata[tag_key].update(value)
            else:
                cell.metadata[tag_key] = value

    def erase(self):
        """
        Erase the content of the selected cells
        """
        for cell in self.iter_cells():
            cell.set_source([])

    def delete(self):
        """
        Delete the selected cells
        """
        self.raw_nb['cells'] = [cell.cell for cell in self.iter_cells(neg=True)]

    def keep(self):
        """
        Delete all the non-selected cells
        """
        self.raw_nb['cells'] = [cell.cell for cell in self.iter_cells()]

    def first(self):
        """
        Return the number of the first selected cell
        :return:
        """
        for cell in self.iter_cells():
            return cell.num

    def last(self):
        """
        Return the number of the last selected cell
        :return:
        """
        for cell in reversed(list(self.iter_cells())):
            return cell.num

    def list(self):
        """
        Return the numbers of the selected cells
        :return:
        """
        return [cell.num for cell in self.iter_cells()]

    def show(self, selector=None, *args,  width=None, style='single', color=None,
             img_color=None, img_width=None, **kwargs):
        """
        Show the selected cells
        :param selector:
        :param args:
        :param width:
        :param style:
        :param color:
        :param img_color:
        :param img_width:
        :param kwargs:
        """
        print(self.to_str(selector, *args, width=width, style=style, color=color, img_color=img_color,
                          img_width=img_width, **kwargs))


class SlideShowMixin(NotebookBase):
    def mark_slideshow(self):
        self.raw_nb['metadata']["celltoolbar"] = "Slideshow"

    def set_slide(self):
        self.tag_slide('slide')

    def set_skip(self):
        self.tag_slide('skip')

    def set_subslide(self):
        self.tag_slide('subslide')

    def set_fragment(self):
        self.tag_slide('fragment')

    def set_notes(self, selector, *args, **kwargs):
        self.tag_slide('notes')

    def tag_slide(self, tag):
        assert tag in {'-', 'skip', 'slide', 'subslide', 'fragment', 'notes'}
        self.tag('slideshow', {'slide_type': tag})

    def tag(self, tag_key, tag):
        raise NotImplemented()

    def delete(self):
        raise NotImplemented()

    def max_cells_per_slide(self, n_cells=3, n_images=1):
        cells_count = 0
        img_count = 0
        for cell in self.iter_cells():
            is_image = has_output_type(cell, 'image/png')
            if is_new_slide(cell):
                cells_count = 1
                img_count = 0
            elif has_slide_type(cell, {'skip', 'fragment', 'notes'}):
                # Don't count
                pass
            else:
                cells_count += 1
            if is_image:
                img_count += 1

            if (n_cells is not None and cells_count > n_cells) or (n_images is not None and img_count > n_images):
                if 'slideshow' in cell.cell['metadata']:
                    cell.metadata['slideshow']['slide_type'] = 'subslide'
                else:
                    cell.metadata['slideshow'] = {'slide_type': 'subslide'}
                cells_count = 1
                img_count = 1 if is_image else 0

    def auto_slide(self, max_cells_per_slide=3, max_images_per_slide=1, *_, delete_empty=True):
        # Delete Empty
        if delete_empty:
            self.select('is_empty').delete()

        # Each title represents
        # TODO: replace using double select
        self.select(['is_markdown', 'contains'], [], '#').set_slide()

        # Create a new slide only
        for cell in reversed(list(self.iter_cells())):
            if cell.num > 0 and is_new_slide(cell.previous_cell):
                if 'slideshow' in cell.cell['metadata']:
                    cell.metadata['slideshow']['slide_type'] = '-'
                else:
                    cell.metadata['slideshow'] = {'slide_type': '-'}

        # Set max cells per slide
        self.max_cells_per_slide(max_cells_per_slide, max_images_per_slide)


class ExportMixin(NotebookBase):
    __exporters = {
        'nbconvert': {
            'html': nbconvert.HTMLExporter,
            'slides': nbconvert.SlidesExporter,
            'python': nbconvert.PythonExporter,
            'markdown': nbconvert.MarkdownExporter,
            'script': nbconvert.ScriptExporter
        }
    }

    @classmethod
    def register_exporter(cls, exporter_name: str, exporter, exporter_type='nbconvert'):
        exporters = cls.__exporters.setdefault(exporter_type, {})
        exporters[exporter_name] = exporter

    @classmethod
    def get_exporter(cls, exporter_name, *args, exporter_type='nbconvert', **kwargs):
        return cls.__exporters[exporter_type][exporter_name](*args, **kwargs)

    def to_json(self):
        return json.dumps(self.raw_nb)

    def to_notebook_node(self):
        if nbformat:
            version = self.raw_nb.get('nbformat', 4)
            return nbformat.reads(self.to_json(), as_version=version)
        else:
            raise ModuleNotFoundError('You need to pip install nbformat to get NotebookNode object')

    def nbconvert(self, exporter_name, path, *args, template_name=None, **kwargs):
        notebook_node = self.to_notebook_node()

        if template_name is not None:
            kwargs['template_name'] = template_name

        exporter = self.get_exporter(exporter_name, *args, exporter_type='nbconvert', **kwargs)

        (body, resources) = exporter.from_notebook_node(notebook_node)

        # Exporting result
        build_directory, file_name = os.path.split(path)
        writer = nbconvert.writers.files.FilesWriter(build_directory=build_directory)

        _, ext = os.path.splitext(file_name)
        if ext:
            resources.pop('output_extension')

        writer.write(body, resources, file_name)

    def to_html(self, path, exclude_code_cell=False, exclude_markdown=False, exclude_raw=False,
                exclude_unknown=False, exclude_input=False, exclude_output=False, **kwargs):
        """
        Exports a basic HTML document.

        :param path: path to export to
        :param exclude_code_cell: This allows you to exclude code cells from all templates if set to True.
        :param exclude_markdown: This allows you to exclude markdown cells from all templates if set to True.
        :param exclude_raw: This allows you to exclude raw cells from all templates if set to True.
        :param exclude_unknown: This allows you to exclude unknown cells from all templates if set to True.
        :param exclude_input: This allows you to exclude input prompts from all templates if set to True.
        :param exclude_output: This allows you to exclude code cell outputs from all templates if set to True.
        :param kwargs: exclude_input_prompt, exclude_output_prompt, ...
        """
        return self.nbconvert('html', path, exclude_code_cell=exclude_code_cell, exclude_markdown=exclude_markdown,
                              exclude_raw=exclude_raw, exclude_unknown=exclude_unknown, exclude_input=exclude_input,
                              exclude_output=exclude_output, **kwargs)

    def to_py(self, path, **kwargs):
        """
        Exports a Python code file.
        Note that the file produced will have a shebang of '#!/usr/bin/env python'
        regardless of the actual python version used in the notebook.

        :param path: path to export to
        """
        return self.nbconvert('python', path, **kwargs)

    def to_md(self, path, exclude_code_cell=False, exclude_markdown=False, exclude_raw=False,
              exclude_unknown=False, exclude_input=False, exclude_output=False, **kwargs):
        """
        Exports to a markdown document (.md)

        :param path: path to export to
        :param exclude_code_cell: This allows you to exclude code cells from all templates if set to True.
        :param exclude_markdown: This allows you to exclude markdown cells from all templates if set to True.
        :param exclude_raw: This allows you to exclude raw cells from all templates if set to True.
        :param exclude_unknown: This allows you to exclude unknown cells from all templates if set to True.
        :param exclude_input: This allows you to exclude input prompts from all templates if set to True.
        :param exclude_output: This allows you to exclude code cell outputs from all templates if set to True.
        :param kwargs: exclude_input_prompt, exclude_output_prompt, ...
        """
        return self.nbconvert('markdown', path, exclude_code_cell=exclude_code_cell, exclude_markdown=exclude_markdown,
                              exclude_raw=exclude_raw, exclude_unknown=exclude_unknown, exclude_input=exclude_input,
                              exclude_output=exclude_output, **kwargs)

    def to_slides(self, path, scroll=True, transition='slide', theme='simple', **kwargs):
        """
        Exports HTML slides with reveal.js

        :param path: path to export to
        :param scroll: If True, enable scrolling within each slide
        :type scroll: bool
        :param transition: Name of the reveal.js transition to use.
        :type transition: none, fade, slide, convex, concave and zoom.
        :param theme: Name of the reveal.js theme to use.
        See https://github.com/hakimel/reveal.js/tree/master/css/theme
        :type theme: beige, black, blood, league, moon, night, serif, simple, sky, solarized, white
        :param kwargs: any additional keyword arguments to nbconvert exporter
        :type kwargs: exclude_code_cell, exclude_markdown, exclude_input, exclude_output, ...
        """
        return self.nbconvert('slides', path, reveal_scroll=scroll, reveal_transition=transition,
                              reveal_theme=theme, **kwargs)

    def to_str(self,  width=None, style='single', color=None, img_color=None, img_width=None):
        return '\n'.join(cell.to_str(width=width, style=style, color=color, img_color=img_color, img_width=img_width)
                         for cell in self.iter_cells())

    def to_text(self, path, *args, **kwargs):
        content = self.to_str(*args, color=False, img_color=False, **kwargs)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

