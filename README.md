# astro-mcp

**Western natal astrology · 星盘 · ホロスコープ · 별자리**

[Shunshi.AI](https://shunshi.ai) local calculation core + Model Context Protocol server.
Python 3.11+, MIT. No API key, database connection or hosted LLM is required.

Local Western natal charts using Skyfield and NASA DE440s: tropical zodiac, Placidus houses with polar Porphyry fallback, planetary positions, retrogrades, nodes and major aspects. Explicit IANA timezone handles historical DST. No solar-time correction. Omit coordinates to omit angles/houses; unknown hour uses noon and returns uncertainty ranges. Supported ephemeris years: 1850–2149.

## Install and connect

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) from its official source. Add this configuration to an MCP client supporting stdio (Claude Desktop, Cursor, Cline or Codex):

```json
{
  "mcpServers": {
    "shunshi-astro": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/shunshi-ai/astro-mcp@v0.1.0",
        "shunshi-astro-mcp"
      ]
    }
  }
}
```

This uses a tagged GitHub source release, **not a PyPI package**. Dependencies are installed from PyPI by uv; the source tag is pinned. Restart the client after adding the server.

For a local checkout:

```bash
git clone https://github.com/shunshi-ai/astro-mcp.git
cd astro-mcp
uv sync --locked
uv run shunshi-astro-mcp
```

The server speaks JSON-RPC on stdout; it intentionally does not print a welcome message.

## Tools

- `getNatalChart` — inspect its MCP schema for validated parameters.

Example parameters for `getNatalChart`:

```json
{
  "birth_time": "2004-05-15T12:00:00",
  "timezone": "Asia/Hong_Kong",
  "latitude": 22.316666666666666,
  "longitude": 114.16666666666667
}
```

Results include a source URL. Computed values and reference text are separate from the calling AI's interpretation; this server does not promise future outcomes.

## Structure and development

`packages/core/src/` contains the reusable core; `src/shunshi_astro_mcp/` contains the MCP adapter. Both ship in one wheel, so no unpublished sibling package is needed. The core can be imported without starting MCP. Calculation provenance is documented in [SOURCE.md](SOURCE.md).

```bash
uv sync --locked
uv run pytest -q
uv build
```

Tests include a real stdio MCP client handshake, tool calls, invalid inputs and recovery. Core reference tests are included where available. No production services are contacted.

## Privacy and license

Inputs stay in the local process; there is no product telemetry. Your MCP client's own model provider may receive tool inputs and outputs according to that client's configuration. Standard Python package installation downloads dependencies. Images, where present, are links; opening them is a separate client action.

MIT © 2026 Shunshi.AI. Preserve any upstream copyright in NOTICE.

Website: [https://shunshi.ai](https://shunshi.ai)

## Ephemeris setup (required once)

Before starting the server, explicitly download the ~32 MB NASA file:

```bash
uvx --from git+https://github.com/shunshi-ai/astro-mcp@v0.1.0 shunshi-astro-mcp --download-ephemeris
```

For a checkout, use `uv run shunshi-astro-mcp --download-ephemeris`.
This connects only to the official NASA JPL URL with a timeout and SHA-256 verification. The file is stored in `~/.cache/shunshi-astro/de440s.bsp`. To use your own copy, set `ASTRO_EPHEMERIS_PATH` in your MCP client's environment. Startup and chart calls never download data; missing files produce an actionable error. Once setup completes, calculations are offline.

## CI template

`docs/github-actions-test.yml` is a ready-to-use GitHub Actions template for Python 3.11–3.13. It is not enabled in this initial release because the publishing credential does not have workflow scope. Tests and installation checks were run locally; enabling hosted CI is a separate step.
