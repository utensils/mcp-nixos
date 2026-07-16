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
