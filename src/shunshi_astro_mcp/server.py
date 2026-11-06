"""Local MCP tools. No production API, database, or hosted LLM calls."""
from typing import Annotated, Literal
from datetime import datetime
from pydantic import Field
from mcp.server.fastmcp import FastMCP

from astrochart import natal_chart

mcp = FastMCP("shunshi-astro-mcp", instructions="Calculate Western natal charts locally with NASA DE440s. Tropical zodiac; Placidus with polar Porphyry fallback. Never invent an unknown birth time/location. No true solar time adjustment. Missing ephemeris is a setup error, not a reason to fabricate a chart.")

@mcp.tool()
def getNatalChart(
    birth_time: str,
    timezone: str,
    latitude: Annotated[float | None, Field(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Field(ge=-180, le=180)] = None,
    hour_unknown: bool = False,
) -> dict:
    """Calculate a natal horoscope / ホロスコープ / 별자리 chart. birth_time is naive local ISO datetime (e.g. 1990-03-24T10:28:00); timezone is an explicit IANA name (e.g. Asia/Seoul). Coordinates must be supplied as a pair. If absent, no Ascendant or houses are returned. Unknown hour uses local noon with uncertainty ranges, without angles/houses. Ephemeris covers 1850–2149. No geocoding, network calls or LLM interpretation."""
    local = datetime.fromisoformat(birth_time)
    if local.tzinfo is not None:
        raise ValueError("birth_time must be local clock time without an offset; use timezone separately")
    if (latitude is None) != (longitude is None):
        raise ValueError("latitude and longitude must be supplied together")
    chart = natal_chart(local=local, lat=latitude, lon=longitude, tz_name=timezone,
                        hour_unknown=hour_unknown, place_known=latitude is not None)
    return {"chart": chart, "source": {"name": "Shunshi.AI", "url": "https://shunshi.ai", "ephemeris": "NASA JPL DE440s"}}

def main():
    import sys
    if sys.argv[1:] == ["--download-ephemeris"]:
        from .setup import download_ephemeris
        print(download_ephemeris())
        return
    if sys.argv[1:]:
        raise SystemExit("usage: shunshi-astro-mcp [--download-ephemeris]")
    mcp.run(transport="stdio")
