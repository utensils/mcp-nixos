"""Contract and shared helpers for the NVF options source.

NVF's standalone/flake interface publishes its option catalogue under
``vim.*``. The NixOS and Home Manager modules wrap the same catalogue under
``programs.nvf.settings.vim.*``. MCP callers may also use the shorter
``programs.nvf.vim.*`` spelling; all supported wrapper paths normalize to the
canonical ``vim.*`` form before lookup or prefix browsing.

The source tracks NVF's latest published unstable documentation and supports
the existing ``search``, ``info``, ``browse``, and ``stats`` actions. Network
loading and action implementations are added in later milestones.
"""

from typing import Final, TypedDict

NVF_SOURCE: Final = "nvf"
NVF_DISPLAY_NAME: Final = "NVF"
NVF_DOCS_TRACK: Final = "unstable"
NVF_CANONICAL_ROOT: Final = "vim"
NVF_SUPPORTED_ACTIONS: Final[frozenset[str]] = frozenset({"search", "info", "browse", "stats"})

# Longest aliases come first to make the intended precedence explicit. Each
# alias names the root itself (without a trailing dot), allowing both a full
# option path and a browse prefix such as ``programs.nvf.vim`` to normalize.
NVF_OPTION_ROOT_ALIASES: Final[tuple[str, ...]] = (
    "config.programs.nvf.settings.vim",
    "programs.nvf.settings.vim",
    "programs.nvf.vim",
)


class NvfOption(TypedDict):
    """Normalized option record shared by NVF cache and source operations."""

    name: str
    type: str
    description: str
    default: str
    example: str
    declarations: list[str]
    url: str


def normalize_nvf_option_path(value: str) -> str:
    """Normalize a canonical or wrapped NVF option path.

    Only recognized option roots are rewritten. Ordinary keyword searches,
    unknown paths, and wrapper-only options such as ``programs.nvf.enable``
    are returned unchanged so later search logic can handle them honestly.
    Prefix comparison is case-insensitive while the unmatched suffix keeps
    its original spelling.
    """
    path = value.strip()
    path_lower = path.lower()

    for alias in NVF_OPTION_ROOT_ALIASES:
        alias_lower = alias.lower()
        if path_lower == alias_lower:
            return NVF_CANONICAL_ROOT
        if path_lower.startswith(alias_lower + "."):
            return NVF_CANONICAL_ROOT + path[len(alias) :]

    return path


def nvf_option_category(name: str) -> str:
    """Return a useful browse/stats category for an NVF option path.

    Since nearly every public NVF option begins with ``vim``, the first two
    path components form the category (for example ``vim.languages``).
    Non-canonical names fall back to their first component.
    """
    normalized = normalize_nvf_option_path(name)
    parts = normalized.split(".") if normalized else []
    if not parts:
        return ""
    if parts[0].lower() == NVF_CANONICAL_ROOT and len(parts) > 1:
        return ".".join(parts[:2])
    return parts[0]
