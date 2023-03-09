# Astrodata build configuration file

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
# sys.path.insert(0, os.path.abspath('.'))

# -- General configuration ------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#
# needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.coverage',
    'sphinx.ext.doctest',
    'sphinx.ext.graphviz',
    'sphinx.ext.ifconfig',
    'sphinx.ext.imgmath',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = '.rst'

# The encoding of source files.
#
# source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'Astrodata Programmer Manual'
copyright = '2022, Association of Universities for Research in Astronomy'
author = 'Ricardo Cardenes'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '3.1'
# The ull version, including alpha/beta/rc tags.
#release = '3.0.x'
#rtdurl = 'release-'+release
release = '3.1.0-dev'
rtdurl = 'v'+release


# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#
today = 'May 2023'
#
# Else, today_fmt is used as the format for a strftime call.
#
# today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This patterns also effect to html_static_path and html_extra_path
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The reST default role (used for this markup: `text`) to use for all
# documents.
default_role = 'obj'

# If true, '()' will be appended to :func: etc. cross-reference text.
#
# add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#
# add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#
# show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
# modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
# keep_warnings = False

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'astropy': ('https://docs.astropy.org/en/stable/', None),
    'gemini_instruments': ('https://dragons-recipe-system-programmers-manual.readthedocs.io/en/latest/', None),
    'geminidr': ('https://dragons-recipe-system-programmers-manual.readthedocs.io/en/latest/', None),
    'matplotlib': ('https://matplotlib.org/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'python': ('https://docs.python.org/3', None),
}

# This is added to the end of RST files - a good place to put substitutions to
# be used globally.
rst_epilog = f"""
.. _`Anaconda`: https://www.anaconda.com/
.. _`Astropy`: http://docs.astropy.org/en/stable/
.. _`Conda`: https://conda.io/docs/
.. _`DRAGONS`: https://dragons.readthedocs.io/
.. _`Numpy`: https://numpy.org/doc/stable/
.. _`Recipe System Programmers Manual`: http://dragons-recipe-system-programmers-manual.readthedocs.io/en/latest/
.. _`Recipe System Users Manual`: http://dragons-recipe-system-users-manual.readthedocs.io/en/latest/

.. |AstroData| replace:: :class:`~astrodata.AstroData`
.. |astrodata| replace:: :mod:`~astrodata`
.. |astropy| replace:: `Astropy`_
.. |DRAGONS| replace:: `DRAGONS`_
.. |geminidr| replace:: :mod:`~geminidr`
.. |gemini_instruments| replace:: :mod:`gemini_instruments`
.. |gemini| replace:: ``gemini``
.. |Mapper| replace:: :class:`~recipe_system.mappers.baseMapper.Mapper`
.. |mappers| replace:: :mod:`recipe_system.mappers`
.. |NDAstroData| replace:: :class:`~astrodata.nddata.NDAstroData`
.. |NDData| replace:: :class:`~astropy.nddata.NDData`
.. |numpy| replace:: `Numpy`_
.. |PrimitiveMapper| replace:: :class:`~recipe_system.mappers.primitiveMapper.PrimitiveMapper`
.. |RecipeMapper| replace:: :class:`~recipe_system.mappers.recipeMapper.RecipeMapper`
.. |recipe_system| replace:: :mod:`recipe_system`
.. |Reduce| replace:: :class:`~recipe_system.reduction.coreReduce.Reduce`
.. |reduce| replace:: ``reduce``
.. |Table| replace:: :class:`~astropy.table.Table`
.. |TagSet| replace:: :class:`~astrodata.TagSet`
"""

# -- Options for HTML output ----------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#
# html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
# html_theme_path = []

# The name for this set of Sphinx documents.
# "<project> v<release> documentation" by default.
#
# html_title = ''

# A shorter title for the navigation bar.  Default is the same as html_title.
#
# html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#
# html_logo = None

# The name of an image file (relative to this directory) to use as a favicon of
# the docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#
# html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# Add any extra paths that contain custom files (such as robots.txt or
# .htaccess) here, relative to this directory. These files are copied
# directly to the root of the documentation.
#
# html_extra_path = []

# If not None, a 'Last updated on:' timestamp is inserted at every page
# bottom, using the given strftime format.
# The empty string is equivalent to '%b %d, %Y'.
#
# html_last_updated_fmt = None

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#
# html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#
# html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#
# html_additional_pages = {}

# If false, no module index is generated.
#
# html_domain_indices = True

# If false, no index is generated.
#
# html_use_index = True

# If true, the index is split into individual pages for each letter.
#
# html_split_index = False

# If true, links to the reST sources are added to the pages.
#
# html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#
# html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#
# html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#
# html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
# html_file_suffix = None

# Language to be used for generating the HTML full-text search index.
# Sphinx supports the following languages:
#   'da', 'de', 'en', 'es', 'fi', 'fr', 'hu', 'it', 'ja'
#   'nl', 'no', 'pt', 'ro', 'ru', 'sv', 'tr', 'zh'
#
# html_search_language = 'en'

# A dictionary with options for the search language support, empty by default.
# 'ja' uses this config value.
# 'zh' user can custom change `jieba` dictionary path.
#
# html_search_options = {'type': 'default'}

# The name of a javascript file (relative to the configuration directory) that
# implements a search results scorer. If empty, the default will be used.
#
# html_search_scorer = 'scorer.js'

# Output file base name for HTML help builder.
htmlhelp_basename = 'AstrodataManual'

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # This will remove blank pages.
    'classoptions': ',openany,oneside',
    'babel': '\\usepackage[english]{babel}',

    # The paper size ('letterpaper' or 'a4paper').
    # 'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    # 'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    # 'preamble': '',
    'preamble': '\\usepackage{appendix} \\setcounter{tocdepth}{0}',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  ('index', 'AstrodataManual.tex', 'Astrodata Manual',
   'DRAGONS Team', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#
latex_logo = 'images/GeminiLogo_new_2014.jpg'

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#
# latex_use_parts = False

# If true, show page references after internal links.
#
# latex_show_pagerefs = False

# If true, show URL addresses after external links.
#
# latex_show_urls = False

# Documents to append as an appendix to all manuals.
#
# latex_appendices = []

# It false, will not define \strong, \code, 	itleref, \crossref ... but only
# \sphinxstrong, ..., \sphinxtitleref, ... To help avoid clash with user added
# packages.
#
# latex_keep_old_macro_names = True

# If false, no module index is generated.
#
# latex_domain_indices = True


# -- Options for manual page output ---------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'astrodatamanual', 'Astrodata Manual',
     ['DRAGONS Team'], 1)
]

# If true, show URL addresses after external links.
#
# man_show_urls = False


# -- Options for Texinfo output -------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'AstrodataManual', 'Astrodata Manual',
   'DRAGONS Team', 'AstrodataManual',
   'Manual for the astrodata package',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#
# texinfo_appendices = []

# If false, no module index is generated.
#
# texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#
# texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#
# texinfo_no_detailmenu = False


# -- Automatically generate API documentation --------------------------------
# -- Enable autoapi ----------------------------------------------------------


def run_api_doc(_):
    """
    Automatic API generator

    This method is used to generate API automatically by importing all the
    modules and sub-modules inside a package.

    It is equivalent to run:
    >>> sphinx-apidoc --force --no-toc --separate --module --output-dir api/ ../../ ../../cal_service

    It is useful because it creates .rst files on the file.

    NOTE
    ----
        This does not work with PyCharm default build. If you want to trigger
        this function, use the standard `$ make html` in the command line.
        The .rst files will be generated. After that, you can use PyCharm's
        build helper.
    """
    build_packages = [
        'astrodata',
        'gemini_instruments'
    ]

    current_path = os.path.abspath(os.path.dirname(__file__))
    root_path = os.path.abspath(os.path.join(current_path, '..', '..'))

    print(("Current Path:", current_path))

    for p in build_packages:

        build_path = os.path.join(root_path, p)

        ignore_paths = ['doc', 'test*', '**/test*']
        ignore_paths = [os.path.join(build_path, i, '*') for i in ignore_paths]

        argv = [
            # "--force",
            "--no-toc",
            # "--separate",
            "--module",
            "--output-dir", "api/",
            build_path
        ] + ignore_paths

        sys.path.insert(0, build_path)

        try:
            # Sphinx 1.7+
            from sphinx.ext import apidoc
            apidoc.main(argv)

        except ImportError:
            # Sphinx 1.6 (and earlier)
            from sphinx import apidoc
            argv.insert(0, apidoc.__file__)
            apidoc.main(argv)


# -- Finishing with a setup that will run always -----------------------------
def setup(app):

    # Adding style in order to have the todos show up in a red box.
    app.add_css_file('todo-styles.css')
    app.add_css_file('rtd_theme_overrides.css')
    app.add_css_file('rtd_theme_overrides_references.css')

    # Automatic API generation
    app.connect('builder-inited', run_api_doc)

rst_epilog = """
.. role:: raw-html(raw)
   :format: html

.. |RSProgShow| replace:: :raw-html:`<a href="https://dragons-recipe-system-programmers-manual.readthedocs.io/en/{v}/">https://dragons-recipe-system-programmers-manual.readthedocs.io/en/{v}/</a>`


""".format(v = rtdurl)
