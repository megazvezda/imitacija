"""Dependency-free checks for dashboard formatting and irregular-time chart handling."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def test_dashboard_formats_and_charts_real_units_without_persistence() -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is optional; required only for frontend helper checks")
    script = Path(__file__).resolve().parents[1] / "src/imitacija/web/dashboard.js"
    assertions = r"""
const assert = require('node:assert/strict');
require(process.argv[1]);
const view = globalThis.ImitacijaView;
assert.equal(view.formatValue(36.694109), '36.69');
assert.equal(view.formatValue(0.00000123), '1.230e-6');
assert.equal(view.formatValue(NaN), '—');
assert.equal(view.escapeHTML('<script>'), '&lt;script&gt;');
const points = [0, 60, 300].map((seconds, i) => ({
  source_value: 63 + i,
  reading: {value: (63 + i) / 60, measured_at: new Date(seconds * 1000).toISOString()}
}));
assert.equal(view.displayed(points[0], 'source'), 63);
assert.equal(view.displayed(points[0], 'wire'), 1.05);
const chart = view.chartSVG(points, 'source');
assert.ok(chart.includes('63.60,')); // Unequal time spacing: 60s is 1/5 of the 300s span.
assert.equal((chart.match(/<circle /g)||[]).length, 3);
assert.ok(chart.includes('00:05:00 UTC'));
assert.ok(view.chartSVG([points[0]], 'source').includes('<circle'));
assert.ok(!view.chartSVG([points[0]], 'source').includes('<polyline'));
assert.ok(!view.chartSVG([], 'source').includes('NaN'));
assert.equal(view.LIMIT, 120);
assert.equal(view.groupOf({scope:'crew', channel:'body_mass'}), 'hydration');
assert.equal(view.groupOf({scope:'crew', channel:'urine_specific_gravity'}), 'hydration');
assert.equal(view.groupOf({scope:'crew', channel:'sweat_sodium_flux'}), 'hydration');
assert.equal(view.groupOf({scope:'environment', channel:'ambient_integrated_dose'}), 'environment');
assert.equal(view.baselineText({
  source_value:74.25, baseline_source_value:75, reading:{channel:'body_mass'}
}), '1% below configured mass baseline');
assert.equal(view.baselineText({
  source_value:75.75, baseline_source_value:75, reading:{channel:'body_mass'}
}), '1% above configured mass baseline');
assert.equal(view.baselineText(null), '');
"""
    subprocess.run(
        [node, "-e", assertions, str(script)], check=True, capture_output=True, text=True
    )
    source = script.read_text()
    assert "localStorage." not in source and "indexedDB." not in source
