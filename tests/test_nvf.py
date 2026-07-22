"""Unit tests for the NVF source contract and shared helpers."""

from unittest.mock import Mock, patch

import pytest
import requests
from mcp_nixos.caches import NvfCache
from mcp_nixos.config import KNOWN_SOURCES, NVF_OPTIONS_URL, APIError
from mcp_nixos.sources.nvf import (
    NVF_DOCS_TRACK,
    NVF_SOURCE,
    NVF_SUPPORTED_ACTIONS,
    NvfOption,
    _browse_nvf_options,
    _format_nvf_option,
    _info_nvf,
    _search_nvf,
    _stats_nvf,
    normalize_nvf_option_path,
    nvf_option_category,
)

NVF_OPTIONS_HTML = """
<html>
  <body>
    <div class="options-container">
      <div class="option" id="option-_module.args">
        <h3 class="option-name">
          <a class="option-anchor" href="#option-_module.args">_module.args</a>
        </h3>
        <div class="option-type">Type: <code>attribute set</code></div>
      </div>

      <div class="option" id="option-vim.languages.nix.enable">
        <h3 class="option-name">
          <a class="option-anchor" href="#option-vim.languages.nix.enable">vim.languages.nix.enable</a>
        </h3>
        <div class="option-type">Type: <code>boolean</code></div>
        <div class="option-description">
          <p>Enable Nix language support.</p>
          <p>Uses <code>nil</code> by default.</p>
        </div>
        <div class="option-default">Default: <code>false</code></div>
        <div class="option-example">Example: <pre><code>{
  enable = true;
}</code></pre></div>
        <div class="option-declared">
          Declared in:
          <a href="modules/languages/nix.nix">&lt;nvf/modules/languages/nix.nix&gt;</a>
          <a href="https://github.com/NotAShelf/nvf/blob/main/modules/languages/default.nix">
            &lt;nvf/modules/languages/default.nix&gt;
          </a>
        </div>
      </div>

      <div class="option" id="option-vim.theme.enable">
        <h3 class="option-name">
          <a class="option-anchor">vim.theme.enable</a>
        </h3>
        <div class="option-type">Type: <code>boolean</code></div>
        <div class="option-description"><p>Enable the configured theme.</p></div>
      </div>

      <div class="option" id="option-vim.malformed">
        <div class="option-description">Missing its name anchor.</div>
      </div>
    </div>
  </body>
</html>
"""


def nvf_options_response(content: bytes | str = NVF_OPTIONS_HTML) -> Mock:
    """Build a successful response mock containing an NVF options document."""
    response = Mock()
    response.content = content
    return response


def nvf_option(
    name: str,
    *,
    option_type: str = "boolean",
    description: str = "",
    default: str = "",
    example: str = "",
    declarations: list[str] | None = None,
) -> NvfOption:
    """Build a normalized NVF option record for source action tests."""
    fragment = name.replace("<", "_").replace(">", "_")
    return {
        "name": name,
        "type": option_type,
        "description": description,
        "default": default,
        "example": example,
        "declarations": declarations or [],
        "url": f"{NVF_OPTIONS_URL}#option-{fragment}",
    }


NVF_SOURCE_OPTIONS = [
    nvf_option(
        "vim.languages.nix.enable",
        description="Whether to enable Nix language support.",
        default="false",
        example="true",
        declarations=["https://github.com/NotAShelf/nvf/blob/main/modules/plugins/languages/nix.nix"],
    ),
    nvf_option(
        "vim.languages.nix.format.type",
        option_type="string",
        description="Select the Nix formatter.",
        default='"alejandra"',
    ),
    nvf_option(
        "vim.languages.lua.enable",
        description="Whether to enable Lua language support.",
        default="false",
    ),
    nvf_option("vim.lsp.enable", description="Whether to enable the LSP client.", default="false"),
    nvf_option("vim.notes.enable", description="Enable a Nix-aware note-taking helper.", default="false"),
    nvf_option("vim.theme.enable", description="Enable the configured color theme.", default="true"),
]


@pytest.mark.unit
class TestNvfSourceContract:
    def test_source_name_and_actions(self):
        assert NVF_SOURCE == "nvf"
        assert NVF_SUPPORTED_ACTIONS == {"search", "info", "browse", "stats"}
        assert NVF_DOCS_TRACK == "unstable"

    def test_source_is_reserved_and_uses_published_options(self):
        assert "nvf" in KNOWN_SOURCES
        assert NVF_OPTIONS_URL == "https://nvf.notashelf.dev/options.html"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("vim.languages.nix.enable", "vim.languages.nix.enable"),
        ("programs.nvf.vim.languages.nix.enable", "vim.languages.nix.enable"),
        ("programs.nvf.settings.vim.languages.nix.enable", "vim.languages.nix.enable"),
        ("config.programs.nvf.settings.vim.languages.nix.enable", "vim.languages.nix.enable"),
        ("programs.nvf.vim", "vim"),
        (" PROGRAMS.NVF.SETTINGS.VIM.languages.nix.enable ", "vim.languages.nix.enable"),
        ("nix diagnostics", "nix diagnostics"),
        ("programs.nvf.enable", "programs.nvf.enable"),
        ("", ""),
    ],
)
def test_normalize_nvf_option_path(given: str, expected: str):
    assert normalize_nvf_option_path(given) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("vim.languages.nix.enable", "vim.languages"),
        ("programs.nvf.vim.lsp.enable", "vim.lsp"),
        ("programs.nvf.settings.vim.treesitter.enable", "vim.treesitter"),
        ("vim", "vim"),
        ("_module.args", "_module"),
        ("", ""),
    ],
)
def test_nvf_option_category(name: str, expected: str):
    assert nvf_option_category(name) == expected


@pytest.mark.unit
class TestNvfCache:
    def test_parse_options_normalizes_complete_and_optional_fields(self):
        options = NvfCache._parse_options(NVF_OPTIONS_HTML)

        assert [option["name"] for option in options] == ["vim.languages.nix.enable", "vim.theme.enable"]
        assert options[0] == {
            "name": "vim.languages.nix.enable",
            "type": "boolean",
            "description": "Enable Nix language support. Uses nil by default.",
            "default": "false",
            "example": "{\n  enable = true;\n}",
            "declarations": [
                "https://nvf.notashelf.dev/modules/languages/nix.nix",
                "https://github.com/NotAShelf/nvf/blob/main/modules/languages/default.nix",
            ],
            "url": "https://nvf.notashelf.dev/options.html#option-vim.languages.nix.enable",
        }
        assert options[1] == {
            "name": "vim.theme.enable",
            "type": "boolean",
            "description": "Enable the configured theme.",
            "default": "",
            "example": "",
            "declarations": [],
            "url": "https://nvf.notashelf.dev/options.html#option-vim.theme.enable",
        }

    def test_get_options_fetches_once_and_reuses_process_cache(self):
        response = nvf_options_response(NVF_OPTIONS_HTML.encode())
        cache = NvfCache()

        with patch("mcp_nixos.caches.requests.get", return_value=response) as get:
            first = cache.get_options()
            second = cache.get_options()

        assert first is second
        assert len(first) == 2
        get.assert_called_once_with(NVF_OPTIONS_URL, timeout=30)
        response.raise_for_status.assert_called_once_with()

    def test_get_options_reports_timeout(self):
        cache = NvfCache()

        with (
            patch("mcp_nixos.caches.requests.get", side_effect=requests.Timeout),
            pytest.raises(APIError, match="Timeout fetching NVF options"),
        ):
            cache.get_options()

    def test_get_options_reports_http_failure(self):
        response = nvf_options_response()
        response.raise_for_status.side_effect = requests.HTTPError("503 Server Error")
        cache = NvfCache()

        with (
            patch("mcp_nixos.caches.requests.get", return_value=response),
            pytest.raises(APIError, match="Failed to fetch NVF options: 503 Server Error"),
        ):
            cache.get_options()

    def test_get_options_rejects_document_without_canonical_options(self):
        response = nvf_options_response(b"<html><body>No option cards</body></html>")
        cache = NvfCache()

        with (
            patch("mcp_nixos.caches.requests.get", return_value=response),
            pytest.raises(APIError, match=r"no canonical vim\.\* options found"),
        ):
            cache.get_options()

        assert cache.options is None

    def test_get_options_wraps_unexpected_parser_failure(self):
        response = nvf_options_response()
        cache = NvfCache()

        with (
            patch("mcp_nixos.caches.requests.get", return_value=response),
            patch.object(cache, "_parse_options", side_effect=ValueError("bad document")),
            pytest.raises(APIError, match="Failed to parse NVF options: bad document"),
        ):
            cache.get_options()

    def test_failed_document_is_not_cached(self):
        bad_response = nvf_options_response(b"<html></html>")
        good_response = nvf_options_response()
        cache = NvfCache()

        with patch("mcp_nixos.caches.requests.get", side_effect=[bad_response, good_response]) as get:
            with pytest.raises(APIError, match=r"no canonical vim\.\* options found"):
                cache.get_options()
            options = cache.get_options()

        assert len(options) == 2
        assert get.call_count == 2


@pytest.mark.unit
class TestNvfSearch:
    def test_search_ranks_option_paths_before_description_matches(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _search_nvf("nix", 10)

        assert "Found 3 NVF options matching 'nix'" in result
        assert result.index("vim.languages.nix.enable") < result.index("vim.languages.nix.format.type")
        assert result.index("vim.languages.nix.format.type") < result.index("vim.notes.enable")
        assert "Type: boolean" in result
        assert "Default: false" in result
        assert "Whether to enable Nix language support." in result

    def test_search_normalizes_wrapped_option_path(self):
        query = "programs.nvf.vim.languages.nix.enable"
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _search_nvf(query, 10)

        assert f"Found 1 NVF options matching '{query}'" in result
        assert "* vim.languages.nix.enable" in result

    def test_search_applies_limit_after_deterministic_sorting(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _search_nvf("enable", 2)

        # Shallower segment matches rank first (vim.lsp.enable at depth 2
        # beats vim.languages.*.enable at depth 3), then alphabetical.
        assert "Found 2 NVF options" in result
        assert "vim.lsp.enable" in result
        assert "vim.notes.enable" in result
        assert "vim.languages.lua.enable" not in result

    def test_search_reports_no_matches(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _search_nvf("does-not-exist", 10)

        assert result == "No NVF options found matching 'does-not-exist'"

    def test_search_propagates_cache_api_error(self):
        with (
            patch("mcp_nixos.sources.nvf.nvf_cache.get_options", side_effect=APIError("unavailable")),
            pytest.raises(APIError, match="unavailable"),
        ):
            _search_nvf("nix", 10)


@pytest.mark.unit
class TestNvfInfo:
    def test_info_normalizes_module_wrapper_and_formats_all_fields(self):
        name = "programs.nvf.settings.vim.languages.nix.enable"
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _info_nvf(name)

        assert "NVF Option: vim.languages.nix.enable" in result
        assert "Type: boolean" in result
        assert "Description: Whether to enable Nix language support." in result
        assert "Default: false" in result
        assert "Example: true" in result
        assert "Declared in: https://github.com/NotAShelf/nvf/" in result
        assert "Documentation: https://nvf.notashelf.dev/options.html#option-vim.languages.nix.enable" in result

    def test_info_matches_canonical_name_case_insensitively(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _info_nvf("VIM.LANGUAGES.LUA.ENABLE")

        assert result.startswith("NVF Option: vim.languages.lua.enable")

    def test_info_suggests_options_below_a_non_exact_path(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _info_nvf("vim.languages.nix")

        assert "Error (NOT_FOUND)" in result
        assert "vim.languages.nix.enable" in result
        assert "vim.languages.nix.format.type" in result

    def test_info_reports_unknown_wrapper_only_option(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _info_nvf("programs.nvf.enable")

        assert result == "Error (NOT_FOUND): NVF option 'programs.nvf.enable' not found"

    def test_format_option_truncates_long_example_and_lists_declarations(self):
        option = nvf_option(
            "vim.test.option",
            example="x" * 501,
            declarations=["https://example.test/one.nix", "https://example.test/two.nix"],
        )

        result = _format_nvf_option(option)

        assert f"Example: {'x' * 500}..." in result
        assert "Declared in:\n* https://example.test/one.nix\n* https://example.test/two.nix" in result


@pytest.mark.unit
class TestNvfBrowse:
    def test_browse_without_prefix_lists_two_component_categories(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _browse_nvf_options("")

        assert "NVF option categories (4 total)" in result
        assert "* vim.languages (3 options)" in result
        assert "* vim.lsp (1 option)" in result
        assert "* vim.notes (1 option)" in result
        assert "* vim.theme (1 option)" in result
        assert result.index("vim.lsp") < result.index("vim.notes") < result.index("vim.theme")

    def test_browse_normalizes_wrapped_prefix_and_trailing_dot(self):
        prefix = "PROGRAMS.NVF.SETTINGS.VIM.languages.nix."
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _browse_nvf_options(prefix)

        assert "NVF options with prefix 'vim.languages.nix' (2 found)" in result
        assert "vim.languages.nix.enable" in result
        assert "vim.languages.nix.format.type" in result
        assert "vim.languages.lua.enable" not in result

    def test_browse_reports_unknown_canonical_prefix(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _browse_nvf_options("programs.nvf.vim.unknown")

        assert result == "No NVF options found with prefix 'vim.unknown'"

    def test_browse_caps_large_prefix_results(self):
        options = [nvf_option(f"vim.plugins.example{i:03}.enable") for i in range(101)]
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=options):
            result = _browse_nvf_options("vim.plugins")

        assert "NVF options with prefix 'vim.plugins' (101 found)" in result
        assert result.count("* vim.plugins.example") == 100
        assert "vim.plugins.example099.enable" in result
        assert "vim.plugins.example100.enable" not in result
        assert "... and 1 more options" in result


@pytest.mark.unit
class TestNvfStats:
    def test_stats_reports_track_totals_and_ranked_categories(self):
        with patch("mcp_nixos.sources.nvf.nvf_cache.get_options", return_value=NVF_SOURCE_OPTIONS):
            result = _stats_nvf()

        assert "NVF Statistics:" in result
        assert "Documentation track: unstable" in result
        assert "Total options: 6" in result
        assert "Categories: 4" in result
        assert "vim.languages: 3" in result
        assert result.index("vim.lsp: 1") < result.index("vim.notes: 1") < result.index("vim.theme: 1")
