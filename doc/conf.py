# pylint: disable=C0103,W0622
"""
Sphinx documentation for Salt
"""
import os
import pathlib
import re
import shutil
import sys
import textwrap
import time
import types

from sphinx.directives.other import TocTree
from sphinx.util import logging

log = logging.getLogger(__name__)

# -- Add paths to PYTHONPATH ---------------------------------------------------
try:
    docs_basepath = os.path.abspath(os.path.dirname(__file__))
except NameError:
    # sphinx-intl and six execute some code which will raise this NameError
    # assume we're in the doc/ directory
    docs_basepath = os.path.abspath(os.path.dirname("."))

addtl_paths = (
    os.pardir,  # salt itself (for autodoc)
    "_ext",  # custom Sphinx extensions
)

for addtl_path in addtl_paths:
    path = os.path.abspath(os.path.join(docs_basepath, addtl_path))
    sys.path.insert(0, path)

# We're now able to import salt
import salt.version  # isort:skip

formulas_dir = os.path.join(os.pardir, docs_basepath, "formulas")

# ----- Intersphinx Settings ------------------------------------------------>
intersphinx_mapping = {
    "python": (
        "https://docs.python.org/3",
        (
            "/usr/share/doc/python{}.{}/html/objects.inv".format(
                sys.version_info[0], sys.version_info[1]
            ),
            "/usr/share/doc/python/html/objects.inv",
            None,
        ),
    )
}
# <---- Intersphinx Settings -------------------------------------------------

# -- General Configuration -----------------------------------------------------

# Set a var if we're building docs for the live site or not
on_saltstack = "SALT_ON_SALTSTACK" in os.environ

project = "Salt"
# This is the default branch on GitHub for the Salt project
repo_primary_branch = "master"
if "LATEST_RELEASE" not in os.environ:
    salt_version = salt.version.__saltstack_version__
else:
    salt_version = salt.version.SaltStackVersion.parse(os.environ["LATEST_RELEASE"])

major_version = str(salt_version.major)
latest_release = ".".join([str(x) for x in salt_version.info])
previous_release = os.environ.get(
    "PREVIOUS_RELEASE", "previous_release"
)  # latest release from previous branch (3002.5)
previous_release_dir = os.environ.get(
    "PREVIOUS_RELEASE_DIR", "previous_release_dir"
)  # path on web server for previous branch (3002.5)
next_release = ""  # next release
next_release_dir = ""  # path on web server for next release branch

# Sphinx variable
# https://www.sphinx-doc.org/en/master/usage/configuration.html#confval-version
version = latest_release

today = ""
copyright = ""
if on_saltstack:
    today = "Generated on {} at {}.".format(
        time.strftime("%B %d, %Y"), time.strftime("%X %Z")
    )
    copyright = time.strftime("%Y")

# < --- START do not merge these settings to other branches START ---> #
build_type = os.environ.get(
    "BUILD_TYPE", repo_primary_branch
)  # latest, previous, master, next
# < --- END do not merge these settings to other branches END ---> #

if build_type == "next":
    release = next_release
elif build_type == "previous":
    release = previous_release
else:  # repo_primary_branch, "latest", or anything else
    release = latest_release

needs_sphinx = "1.3"

spelling_lang = "en_US"
spelling_show_suggestions = True
language = "en"
locale_dirs = [
    "_locale",
]

master_doc = "index"
templates_path = ["_templates"]
exclude_patterns = ["_build", "_incl/*", "ref/cli/_includes/*.rst"]

extensions = [
    "saltdomain",  # Must come early
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.autosummary",
    "sphinx.ext.extlinks",
    "sphinx.ext.imgconverter",
    "sphinx.ext.intersphinx",
    "sphinxcontrib.httpdomain",
    "saltrepo",
    "myst_parser",
    "sphinx_design",
    #'saltautodoc', # Must be AFTER autodoc
]

# Only enable spell-checking if enchant library is available
# This is optional for package builds but useful during development
try:
    import enchant

    extensions.append("sphinxcontrib.spelling")
except ImportError:
    log.info("Spell-checking disabled: enchant library not available")

modindex_common_prefix = ["salt."]

autosummary_generate = True
autosummary_generate_overwrite = False

# Smart dependency handling for documentation builds
# For man pages (lightweight CLI docs), we auto-mock missing dependencies
# For full HTML docs, we fail with helpful errors about what's missing
autodoc_mock_imports = []

# Detect if we're building man pages only (lightweight build)
# Man pages only document CLI tools and don't need full Salt imports
building_man_only = "man" in sys.argv and "html" not in sys.argv

# External dependencies that Salt imports at module level
# These need to be available for full HTML docs (autodoc) but can be mocked for man pages
_SALT_DEPENDENCIES = [
    "backports",  # Not available in Python 3.13+
    "distro",
    "jinja2",
    "looseversion",
    "msgpack",
    "packaging",
    "yaml",
]

_missing_deps = []
for dep in _SALT_DEPENDENCIES:
    try:
        __import__(dep)
    except ImportError:
        _missing_deps.append(dep)
        # Always mock missing dependencies to allow build to proceed
        autodoc_mock_imports.append(dep)

if _missing_deps:
    if building_man_only:
        # For man pages, this is expected - they don't need Salt modules
        log.info(
            "Building man pages with mocked dependencies: %s (this is normal for man pages)",
            ", ".join(_missing_deps),
        )
    else:
        # For HTML/full builds, warn that docs may be incomplete
        log.warning(
            "\n"
            "=" * 70 + "\n"
            "WARNING: Missing dependencies for full documentation build:\n"
            "  %s\n\n"
            "Autodoc will use mocked modules. Documentation will be generated but\n"
            "may be incomplete or show incorrect type hints.\n\n"
            "For complete documentation, install with:\n"
            "  pip install %s\n" + "=" * 70,
            ", ".join(_missing_deps),
            " ".join(_missing_deps),
        )

# strip git rev as there won't necessarily be a release based on it
stripped_release = re.sub(r"-\d+-g[0-9a-f]+$", "", release)

# Define a substitution for linking to the latest release tarball
rst_prolog = """\
.. |current_release_doc| replace:: :doc:`/topics/releases/{release}`
.. |saltrepo| replace:: https://github.com/saltstack/salt
.. _`salt-users`: https://groups.google.com/forum/#!forum/salt-users
.. _`salt-announce`: https://groups.google.com/forum/#!forum/salt-announce
.. _`salt-packagers`: https://groups.google.com/forum/#!forum/salt-packagers
.. _`salt-discord`: https://discord.com/invite/J7b7EscrAs

""".format(
    release=stripped_release
)

# A shortcut for linking to tickets on the GitHub issue tracker
extlinks = {
    "blob": (
        "https://github.com/saltstack/salt/blob/%s/%%s" % repo_primary_branch,
        "%s",
    ),
    "issue": ("https://github.com/saltstack/salt/issues/%s", "issue %s"),
    "pull": ("https://github.com/saltstack/salt/pull/%s", "PR %s"),
    "formula_url": ("https://github.com/saltstack-formulas/%s", "url %s"),
}

myst_gfm_only = True

# ----- Localization -------------------------------------------------------->
locale_dirs = ["locale/"]
gettext_compact = False
# <---- Localization ---------------------------------------------------------


### HTML options
html_theme = "pydata_sphinx_theme"
html_title = ""
html_short_title = "Salt"

html_static_path = ["_static"]
html_logo = "_static/salt-logo-full.svg"
html_favicon = "favicon.ico"
smartquotes = False

# Map the current build to a `version_match` value the version-switcher JSON
# at https://docs.saltproject.io/en/master/_static/switcher.json understands.
# - master/development builds   -> "master"
# - tagged release builds       -> the major version series ("3006", "3007", ...)
if build_type == repo_primary_branch:
    switcher_version = "master"
else:
    switcher_version = major_version

html_theme_options = {
    "logo": {
        "alt_text": "Salt Project Documentation",
    },
    "switcher": {
        "json_url": "https://docs.saltproject.io/en/master/_static/switcher.json",
        "version_match": switcher_version,
    },
    "check_switcher": False,
    # Avoid PyData's link-shortening transform: it calls urlparse() on refuris and
    # crashes on literal patterns like ``http://hostname[:port]`` in docstrings.
    "shorten_urls": False,
    "navbar_start": ["navbar-logo", "version-switcher"],
    "navbar_center": ["navbar-nav"],
    "navbar_end": ["theme-switcher", "navbar-icon-links"],
    "navbar_persistent": ["search-button"],
    "external_links": [
        {"name": "Install Guide", "url": "https://docs.saltproject.io/salt/install-guide/en/latest/"},
        {"name": "User Guide", "url": "https://docs.saltproject.io/salt/user-guide/en/latest/"},
        {"name": "Downloads", "url": "https://packages.broadcom.com/artifactory/saltproject-generic/"},
        {"name": "Develop", "url": "https://docs.saltproject.io/en/master/topics/development/"},
    ],
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/saltstack/salt",
            "icon": "fa-brands fa-github",
        },
        {
            "name": "Discord",
            "url": "https://discord.com/invite/J7b7EscrAs",
            "icon": "fa-brands fa-discord",
        },
        {
            "name": "Salt Project",
            "url": "https://saltproject.io/",
            "icon": "fa-solid fa-globe",
        },
    ],
    "show_version_warning_banner": True,
    "use_edit_page_button": True,
    "footer_start": ["copyright", "last-updated"],
    "footer_end": ["sphinx-version"],
}

# Sidebars: rely on the PyData defaults everywhere except the landing page
# (no meaningful TOC to show) and module reference pages, where we still
# want the in-page module function index produced by modules-sidebar.html.
html_sidebars = {
    "index": [],
    "ref/**/all/salt.*": [
        "sidebar-nav-bs",
        "modules-sidebar.html",
    ],
    "ref/formula/all/*": [],
}

html_context = {
    "github_user": "saltstack",
    "github_repo": "salt",
    "github_version": repo_primary_branch,
    "doc_path": "doc",
    "repo_primary_branch": repo_primary_branch,
}

html_additional_pages = {
    "404": "404.html",
}

html_use_index = True
html_last_updated_fmt = "%b %d, %Y"
html_show_sourcelink = False
html_show_sphinx = True
html_show_copyright = True

### Latex options

latex_documents = [
    ("reference", "Salt.tex", "Salt Documentation", "VMware, Inc.", "manual"),
]

latex_logo = "_static/salt-logo.png"

latex_elements = {
    "inputenc": "",  # use XeTeX instead of the inputenc LaTeX package.
    "utf8extra": "",
    "preamble": r"""
    \usepackage{fontspec}
    \setsansfont{Linux Biolinum O}
    \setromanfont{Linux Libertine O}
    \setmonofont{Source Code Pro}
""",
}
### Linux Biolinum, Linux Libertine: http://www.linuxlibertine.org/
### Source Code Pro: https://github.com/adobe-fonts/source-code-pro/releases


### Linkcheck options
linkcheck_ignore = [
    r"http://127.0.0.1",
    r"http://salt:\d+",
    r"http://local:\d+",
    r"https://console.aws.amazon.com",
    r"http://192.168.33.10",
    r"http://domain:\d+",
    r"http://123.456.789.012:\d+",
    r"http://localhost",
    r"https://groups.google.com/forum/#!forum/salt-users",
    r"https://www.elastic.co/logstash/docs/latest/inputs/udp",
    r"https://www.elastic.co/logstash/docs/latest/inputs/zeromq",
    r"http://www.youtube.com/saltstack",
    r"https://raven.readthedocs.io",
    r"https://getsentry.com",
    r"https://salt-cloud.readthedocs.io",
    r"https://salt.readthedocs.io",
    r"http://www.pip-installer.org/",
    r"http://www.windowsazure.com/",
    r"https://github.com/watching",
    r"dash-feed://",
    r"https://github.com/saltstack/salt/",
    r"https://bootstrap.saltproject.io",
    r"https://raw.githubusercontent.com/saltstack/salt-bootstrap/stable/bootstrap-salt.sh",
    r"media.readthedocs.org/dash/salt/latest/salt.xml",
    r"https://portal.aws.amazon.com/gp/aws/securityCredentials",
    r"dash-feed://https%3A//media.readthedocs.org/dash/salt/latest/salt.xml",
    r"(?i)dns:.*",
    r"TCP:4506",
    r"https?://",
    r"https://cloud.github.com/downloads/saltstack/.*",
    r"https://INFOBLOX/.*",
    r"https://SOMESERVERIP:.*",
    r"https://community.saltstack.com/.*",
    # GitHub Users
    r"https://github.com/[^/]$",
    # GitHub Salt Forks
    r"https://github.com/[^/]/salt$",
    r"tag:key=value",
    r"jdbc:mysql:.*",
    r"http:post",
]
linkcheck_exclude_documents = [
    r"topics/releases/(2015|2016)\..*\.rst",
    r"topics/releases/saltapi/0\.8\.0.*",
]
linkcheck_timeout = 10
linkcheck_anchors = False

### Manpage options
# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
authors = [
    "Thomas S. Hatch <thatch45@gmail.com> and many others, please see the Authors file",
]

man_pages = [
    ("ref/cli/salt", "salt", "salt", authors, 1),
    ("ref/cli/salt-master", "salt-master", "salt-master Documentation", authors, 1),
    ("ref/cli/salt-minion", "salt-minion", "salt-minion Documentation", authors, 1),
    ("ref/cli/salt-key", "salt-key", "salt-key Documentation", authors, 1),
    ("ref/cli/salt-cp", "salt-cp", "salt-cp Documentation", authors, 1),
    ("ref/cli/salt-call", "salt-call", "salt-call Documentation", authors, 1),
    ("ref/cli/salt-proxy", "salt-proxy", "salt-proxy Documentation", authors, 1),
    ("ref/cli/salt-syndic", "salt-syndic", "salt-syndic Documentation", authors, 1),
    ("ref/cli/salt-run", "salt-run", "salt-run Documentation", authors, 1),
    ("ref/cli/salt-ssh", "salt-ssh", "salt-ssh Documentation", authors, 1),
    ("ref/cli/salt-cloud", "salt-cloud", "Salt Cloud Command", authors, 1),
    ("ref/cli/salt-api", "salt-api", "salt-api Command", authors, 1),
    ("ref/cli/spm", "spm", "Salt Package Manager Command", authors, 1),
]


def skip_mod_init_member(app, what, name, obj, skip, options):
    # pylint: disable=too-many-arguments,unused-argument
    if name.startswith("_"):
        return True
    if isinstance(obj, types.FunctionType) and obj.__name__ == "mod_init":
        return True
    return False


def _normalize_version(args):
    _, path = args
    return ".".join([x.zfill(4) for x in (path.split("/")[-1].split("."))])


class ReleasesTree(TocTree):
    option_spec = dict(TocTree.option_spec)

    def run(self):
        rst = super().run()
        entries = rst[0][0]["entries"][:]
        entries.sort(key=_normalize_version, reverse=True)
        rst[0][0]["entries"][:] = entries
        return rst


def copy_release_templates_pre(app):
    app._copied_release_files = []
    docs_path = pathlib.Path(docs_basepath)
    release_files_dir = docs_path / "topics" / "releases"
    release_template_files_dir = release_files_dir / "templates"
    for fpath in release_template_files_dir.iterdir():
        dest = release_files_dir / fpath.name.replace(".template", "")
        if dest.exists():
            continue
        log.info(
            "Copying '%s' -> '%s' just for this build ...",
            fpath.relative_to(docs_path),
            dest.relative_to(docs_path),
        )
        app._copied_release_files.append(dest)
        shutil.copyfile(fpath, dest)


def copy_release_templates_post(app, exception):
    docs_path = pathlib.Path(docs_basepath)
    for fpath in app._copied_release_files:
        log.info(
            "The release file '%s' was copied for the build, but its not in "
            "version control system. Deleting.",
            fpath.relative_to(docs_path),
        )
        fpath.unlink()


def extract_module_deprecations(app, what, name, obj, options, lines):
    """
    Add a warning to the modules being deprecated into extensions.
    """
    # https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#event-autodoc-process-docstring
    if what != "module":
        # We're only interested in module deprecations
        return

    try:
        deprecated_info = obj.__deprecated__
    except AttributeError:
        # The module is not deprecated
        return

    _version, _extension, _url = deprecated_info
    msg = textwrap.dedent(
        f"""
        .. warning::

            This module will be removed from Salt in version {_version} in favor of
            the `{_extension} Salt Extension <{_url}>`_.

        """
    )
    # Modify the docstring lines in-place
    lines[:] = msg.splitlines() + lines


def setup(app):
    app.add_directive("releasestree", ReleasesTree)
    app.connect("autodoc-skip-member", skip_mod_init_member)
    app.connect("builder-inited", copy_release_templates_pre)
    app.connect("build-finished", copy_release_templates_post)
    app.connect("autodoc-process-docstring", extract_module_deprecations)
