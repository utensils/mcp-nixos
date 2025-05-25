# MCP-NixOS Server Refactoring Project

## Objective
You are tasked with completely refactoring the MCP-NixOS server from an over-engineered ~5000+ line codebase to a clean, maintainable ~200-300 line implementation following MCP best practices. This is a complete architectural overhaul, not incremental improvements.

## Development Environment (Nix Flakes)
This project uses **Nix flakes** for development environment management. You MUST use the Nix development environment for all operations:

### Key Commands:
- **Enter dev environment**: `nix develop` (auto-activates Python venv)
- **Run any command**: `nix develop -c <command>` (runs command in dev environment)
- **Run server**: `nix develop -c run`
- **Run tests**: `nix develop -c run-tests` (supports `--unit` and `--integration` flags)
- **Format code**: `nix develop -c format`
- **Type check**: `nix develop -c typecheck`
- **Build package**: `nix develop -c build`

### Environment Features:
- Python 3.11 with all dependencies pre-configured
- Virtual environment automatically created in `.venv/`
- Cross-platform support (Linux, macOS, Windows via WSL)
- All development tools available (pytest, black, flake8, pyright)
- Package building and distribution tools included

## Reference Documents
I have provided two critical reference documents:
1. **MCP-NixOS Refactoring Guide** - Detailed technical plan and target architecture
2. **MCP Evals Guide** - Testing approach for AI performance validation

Please thoroughly read and reference these documents throughout the refactoring process.

## Current State Analysis
The existing codebase has these major problems:
- Over-engineered with excessive abstraction layers
- Complex caching system with filesystem persistence and atomic writes
- Background threading and async initialization
- Multiple context classes and resource management systems
- Mixed output formats instead of structured data
- Violates MCP best practices (should be simple, stateless, fast-starting)

## Target Architecture
Based on the refactoring guide, create:
- **Single main server file** (~200-300 lines) with direct tool implementations
- **Simple formatter utility** (~50 lines) for consistent XML output
- **Structured XML responses** for all tools following documented patterns
- **Direct API calls** with no abstraction layers
- **Stateless operation** with fast startup
- **Comprehensive test coverage** including basic evals

## Project Execution Plan

### Phase 1: Analysis and Setup (First)
1. **Analyze existing codebase structure**
   - Map current functionality and API endpoints
   - Identify all existing tools and their current interfaces  
   - Document current test coverage and patterns: `nix develop -c run-tests`
   - Create migration tracking document

2. **Verify development environment**
   - Test Nix flake setup: `nix develop`
   - Verify all commands work: `nix develop -c run`, `nix develop -c run-tests`
   - Check Python environment and dependencies
   - Validate build process: `nix develop -c build`

3. **Create new project structure**
   ```
   mcp_nixos/
   ├── server.py          # Main server (200-300 lines)
   ├── formatters.py      # XML output utilities (~50 lines)
   ├── __init__.py        # Version and exports
   └── tests/
       ├── test_tools.py      # Tool functionality tests
       ├── test_formatters.py # Output format tests
       └── test_evals.py      # Basic AI performance evals
   ```

4. **Update flake.nix if needed**
   - Ensure dependencies match new simplified architecture
   - Remove unused dependencies from the flake
   - Verify package builds correctly with new structure

### Phase 2: Core Server Implementation
1. **Implement main server.py**
   - FastMCP server setup with metadata
   - API configuration constants (NixOS, Home Manager, Darwin URLs/auth)
   - Channel mapping and validation
   - All tool functions with direct API calls
   - Consistent error handling with XML format

2. **Tool Implementation Priority** (implement in this order):
   ```python
   # Core NixOS tools (highest priority)
   @mcp.tool()
   def nixos_search(query: str, type: str = "packages", limit: int = 20, channel: str = "unstable") -> str:
   
   @mcp.tool() 
   def nixos_info(name: str, type: str = "package", channel: str = "unstable") -> str:
   
   @mcp.tool()
   def nixos_stats(channel: str = "unstable") -> str:
   
   # Home Manager tools (medium priority)
   @mcp.tool()
   def home_manager_search(query: str, limit: int = 20) -> str:
   
   @mcp.tool()
   def home_manager_info(name: str) -> str:
   
   @mcp.tool()
   def home_manager_list_options() -> str:
   
   @mcp.tool()  
   def home_manager_options_by_prefix(option_prefix: str) -> str:
   
   # Darwin tools (lower priority) 
   @mcp.tool()
   def darwin_search(query: str, limit: int = 20) -> str:
   
   @mcp.tool()
   def darwin_info(name: str) -> str:
   
   # Discovery tools (lowest priority)
   @mcp.tool()
   def discover_tools() -> str:
   ```

3. **Implement formatters.py**
   - XML formatting utilities with proper escaping
   - Consistent error formatting
   - Result formatting for packages, options, and search results
   - Helper functions for common XML patterns

### Phase 3: Testing Implementation
1. **Port existing test patterns**
   - Analyze current test coverage: `nix develop -c run-tests`
   - Create equivalent tests for new simplified tools
   - Ensure all current functionality is tested
   - Maintain or improve test coverage percentage

2. **Implement basic evals** (reference the evals guide)
   - Package discovery scenarios (find VSCode, git commands)
   - Service configuration scenarios (nginx, postgresql setup)  
   - Home Manager vs system configuration guidance
   - Error handling and edge cases

3. **Test execution and validation**
   - All tests must pass: `nix develop -c run-tests`
   - Run unit tests: `nix develop -c run-tests -- --unit`
   - Run integration tests: `nix develop -c run-tests -- --integration`
   - Performance comparison with original (should be faster)
   - Code quality checks: `nix develop -c lint` and `nix develop -c typecheck`

### Phase 4: Integration and Cleanup
1. **Update package configuration**
   - Verify flake.nix builds correctly: `nix develop -c build`
   - Test package installation: `nix build`
   - Update imports and dependencies in flake.nix as needed
   - Ensure version compatibility in pyproject.toml

2. **Remove old implementation**
   - Delete obsolete directories: `cache/`, `contexts/`, `resources/`, `clients/`, `utils/`
   - Remove files: `logging.py`, `run.py`, old `server.py`
   - Update flake.nix to remove unused dependencies
   - Clean up unused imports

3. **Final validation**
   - Complete test suite passes: `nix develop -c run-tests`
   - Code quality checks pass: `nix develop -c lint` and `nix develop -c typecheck`
   - Package builds successfully: `nix develop -c build`
   - Basic evals demonstrate AI usability
   - Performance validation (faster startup)
   - Nix package builds and runs: `nix build && ./result/bin/mcp-nixos --help`

## Implementation Requirements

### Code Quality Standards
- **Type hints** on all functions
- **Docstrings** with clear parameter and return descriptions  
- **Error handling** with informative XML error responses
- **Input validation** with appropriate limits and checks
- **Consistent code style** following Python conventions

### XML Output Format Requirements
All tools must return structured XML following these patterns:

```python
# Search results
<package_search>
  <query>firefox</query>
  <results count="3">
    <package>
      <name>firefox</name>
      <version>120.0</version>
      <description>Mozilla Firefox web browser</description>
    </package>
  </results>
</package_search>

# Info responses  
<package_info>
  <name>firefox</name>
  <version>120.0</version>
  <description>Mozilla Firefox web browser</description>
  <homepage>https://firefox.com</homepage>
  <license>MPL-2.0</license>
</package_info>

# Errors
<error>
  <code>INVALID_CHANNEL</code>
  <message>Invalid channel 'invalid'. Must be: unstable, stable, 24.11, 25.05, beta</message>
</error>
```

### API Integration Requirements
- **Direct HTTP calls** using requests library
- **Proper authentication** for NixOS Elasticsearch API
- **Timeout handling** (10 second max per request)
- **Rate limiting respect** (reasonable delays between requests)
- **Error response parsing** from external APIs

### Testing Requirements
- **Maintain current test coverage** percentage or improve it
- **Test both success and error cases** for each tool
- **Mock external API calls** appropriately in tests
- **Include basic eval scenarios** demonstrating AI usability
- **Performance tests** showing improved startup time
- **Use Nix environment for all testing**: `nix develop -c run-tests`
- **Validate code quality**: `nix develop -c lint` and `nix develop -c typecheck`

## Progress Tracking
Throughout the refactoring, maintain a progress document that tracks:

1. **Completion Status**
   ```
   Phase 1: Analysis and Setup          [■■■□] 75%
   Phase 2: Core Server Implementation  [■□□□] 25%  
   Phase 3: Testing Implementation      [□□□□] 0%
   Phase 4: Integration and Cleanup     [□□□□] 0%
   ```

2. **Tool Implementation Status**
   ```
   nixos_search        [DONE] ✓ Tested
   nixos_info          [DONE] ✓ Tested  
   nixos_stats         [IN PROGRESS]
   home_manager_search [TODO]
   ...
   ```

3. **Issues and Decisions Log**
   - Document any challenges encountered
   - Record architectural decisions made
   - Note any deviations from the original plan

4. **Metrics Tracking**
   - Lines of code: Before vs After
   - Test coverage: Before vs After  
   - Startup time: Before vs After
   - Memory usage: Before vs After

## Success Criteria
The refactoring is complete when:

1. **All existing functionality** is preserved with same or better API interface
2. **All tests pass** with maintained or improved coverage
3. **Basic evals demonstrate** AI can successfully use the tools
4. **Codebase is dramatically simplified** (~95% reduction in lines of code)
5. **Server starts fast** (< 1 second vs current complex initialization)
6. **XML output is consistent** and well-structured across all tools
7. **No unused code remains** from the old implementation

## Execution Instructions

1. **Start by entering the Nix development environment**: `nix develop`
2. **Read both reference documents thoroughly**
3. **Follow the phases in order** - do not skip ahead
4. **Use Nix commands for all operations**:
   - Tests: `nix develop -c run-tests`
   - Formatting: `nix develop -c format`
   - Type checking: `nix develop -c typecheck`
   - Building: `nix develop -c build`
   - Running server: `nix develop -c run`
5. **Test continuously** - don't implement everything then test
6. **Track progress** - update status after each major milestone
7. **Ask for clarification** if any requirements are unclear
8. **Clean up as you go** - don't leave old code around
9. **Document decisions** - record any significant changes to the plan
10. **Maintain flake.nix** - update dependencies as you simplify the codebase

## Final Notes
This is a complete architectural overhaul that will result in a dramatically simpler, more maintainable, and more AI-friendly MCP server. The goal is not just to reduce code complexity, but to create a server that better serves its purpose of enabling AI assistants to help users with NixOS, Home Manager, and Darwin configurations.

Focus on creating clean, direct implementations that follow MCP best practices rather than preserving complex abstractions from the original codebase. The end result should be professional, easy to understand, and a model for how MCP servers should be built.