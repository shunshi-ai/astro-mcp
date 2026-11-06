# astro calculation core

Bundled in the `shunshi-astro-mcp` distribution. Import `astrochart` without starting the MCP server.

See the root README for installation, input conventions and capability limits, and SOURCE.md for calculation provenance.

```python
from datetime import datetime
from astrochart import natal_chart
print(natal_chart(local=datetime(2004, 5, 15, 12), lat=22.3193, lon=114.1694, tz_name="Asia/Hong_Kong"))
```
