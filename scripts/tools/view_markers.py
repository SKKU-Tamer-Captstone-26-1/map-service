from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.db.verify_map_view_schema import resolve_database_url


LAYER_COLORS = {
    "bar": "#E8502A",
    "pub": "#F0A500",
    "liquor_shop": "#5B8DD9",
    "outdoor_spot": "#4CAF50",
    "restaurant": "#9C27B0",
    "convenience_store": "#00BCD4",
    "other": "#9E9E9E",
}

LAYER_LABELS_KO = {
    "bar": "바",
    "pub": "펍",
    "liquor_shop": "주류 판매점",
    "outdoor_spot": "야외 장소",
    "restaurant": "음식점",
    "convenience_store": "편의점",
    "other": "기타",
}


def fetch_markers(database_url: str) -> list[dict]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    m.id::text AS id,
                    m.label,
                    m.layer_code,
                    ST_Y(m.location::geometry) AS latitude,
                    ST_X(m.location::geometry) AS longitude,
                    COALESCE(m.filter_json->>'address', m.filter_json->>'road_address', '') AS address,
                    COALESCE(m.filter_json->>'canonical', 'false') = 'true' AS canonical,
                    m.visibility::text AS visibility,
                    m.published_revision
                FROM map_view.markers m
                WHERE m.visibility = 'visible'
                ORDER BY m.layer_code, m.label
                """
            )
            return [dict(row) for row in cur.fetchall()]


def fetch_layer_counts(database_url: str) -> list[dict]:
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT layer_code, COUNT(*) AS cnt
                FROM map_view.markers
                WHERE visibility = 'visible'
                GROUP BY layer_code
                ORDER BY cnt DESC
                """
            )
            return [dict(row) for row in cur.fetchall()]


def build_html(markers: list[dict], layer_counts: list[dict]) -> str:
    total = len(markers)
    layer_stats = {r["layer_code"]: r["cnt"] for r in layer_counts}
    layer_stat_rows = "".join(
        f'<tr><td style="color:{LAYER_COLORS.get(lc,"#888")}">{LAYER_LABELS_KO.get(lc, lc)}</td>'
        f'<td style="text-align:right">{cnt:,}</td></tr>'
        for lc, cnt in layer_stats.items()
    )

    canonical_count = sum(1 for m in markers if m["canonical"])

    markers_json = json.dumps(
        [
            {
                "id": m["id"],
                "label": m["label"],
                "layerCode": m["layer_code"],
                "lat": float(m["latitude"]),
                "lon": float(m["longitude"]),
                "address": m["address"] or "",
                "canonical": bool(m["canonical"]),
            }
            for m in markers
        ],
        ensure_ascii=False,
    )

    layer_colors_json = json.dumps(LAYER_COLORS)
    layer_labels_json = json.dumps(LAYER_LABELS_KO, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <title>Map Markers Viewer ({total:,}개)</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; display: flex; height: 100vh; overflow: hidden; }}
    #sidebar {{
      width: 260px; min-width: 260px; background: #1a1a2e; color: #e0e0e0;
      display: flex; flex-direction: column; overflow: hidden;
    }}
    #sidebar-header {{
      padding: 16px; background: #16213e; border-bottom: 1px solid #0f3460;
    }}
    #sidebar-header h1 {{ font-size: 15px; font-weight: 700; color: #e94560; margin-bottom: 4px; }}
    #sidebar-header p {{ font-size: 12px; color: #aaa; }}
    #layer-filter {{ padding: 12px 16px; border-bottom: 1px solid #0f3460; }}
    #layer-filter h2 {{ font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }}
    .layer-chip {{
      display: flex; align-items: center; gap: 8px; padding: 6px 8px;
      border-radius: 6px; cursor: pointer; margin-bottom: 4px; user-select: none;
      transition: background .15s;
    }}
    .layer-chip:hover {{ background: #0f3460; }}
    .layer-chip.off {{ opacity: .35; }}
    .layer-dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }}
    .layer-name {{ font-size: 13px; flex: 1; }}
    .layer-count {{ font-size: 11px; color: #888; }}
    #stats-panel {{ padding: 12px 16px; border-bottom: 1px solid #0f3460; }}
    #stats-panel h2 {{ font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }}
    #stats-panel table {{ width: 100%; font-size: 12px; border-collapse: collapse; }}
    #stats-panel td {{ padding: 3px 0; }}
    #detail-panel {{
      padding: 12px 16px; flex: 1; overflow-y: auto;
      border-top: 1px solid #0f3460; display: none;
    }}
    #detail-panel h2 {{ font-size: 11px; font-weight: 600; color: #888; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 8px; }}
    #detail-name {{ font-size: 14px; font-weight: 700; color: #e0e0e0; margin-bottom: 4px; }}
    #detail-layer {{ font-size: 12px; margin-bottom: 4px; }}
    #detail-address {{ font-size: 11px; color: #aaa; line-height: 1.4; }}
    #detail-id {{ font-size: 10px; color: #555; margin-top: 6px; word-break: break-all; }}
    #map {{ flex: 1; }}
    .custom-icon {{ border-radius: 50%; border: 2px solid white; box-shadow: 0 1px 4px rgba(0,0,0,.5); }}
  </style>
</head>
<body>
  <div id="sidebar">
    <div id="sidebar-header">
      <h1>Map Markers Viewer</h1>
      <p>총 <strong>{total:,}</strong>개 &nbsp;|&nbsp; canonical <strong>{canonical_count}</strong>개</p>
    </div>
    <div id="layer-filter">
      <h2>레이어 필터</h2>
      <div id="layer-chips"></div>
    </div>
    <div id="stats-panel">
      <h2>레이어별 통계</h2>
      <table>{layer_stat_rows}</table>
    </div>
    <div id="detail-panel">
      <h2>마커 정보</h2>
      <div id="detail-name"></div>
      <div id="detail-layer"></div>
      <div id="detail-address"></div>
      <div id="detail-id"></div>
    </div>
  </div>
  <div id="map"></div>

  <script>
    const MARKERS_DATA = {markers_json};
    const LAYER_COLORS = {layer_colors_json};
    const LAYER_LABELS = {layer_labels_json};

    const map = L.map('map').setView([37.5, 127.0], 11);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }}).addTo(map);

    const clusterGroup = L.markerClusterGroup({{
      chunkedLoading: true,
      maxClusterRadius: 40,
      spiderfyOnMaxZoom: true,
    }});

    const layerMarkers = {{}};
    const activeLayerCodes = new Set(Object.keys(LAYER_COLORS));

    function makeIcon(layerCode, canonical) {{
      const color = LAYER_COLORS[layerCode] || '#888';
      if (canonical) {{
        return L.divIcon({{
          html: `<div style="width:16px;height:16px;border-radius:50%;background:${{color}};border:3px solid #FFD700;box-shadow:0 0 6px #FFD700,0 1px 4px rgba(0,0,0,.6)"></div>`,
          iconSize: [16, 16],
          iconAnchor: [8, 8],
          className: '',
        }});
      }}
      return L.divIcon({{
        html: `<div style="width:10px;height:10px;border-radius:50%;background:${{color}};border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>`,
        iconSize: [14, 14],
        iconAnchor: [7, 7],
        className: '',
      }});
    }}

    function showDetail(m) {{
      document.getElementById('detail-panel').style.display = 'block';
      document.getElementById('detail-name').textContent = m.label;
      const layerEl = document.getElementById('detail-layer');
      layerEl.textContent = LAYER_LABELS[m.layerCode] || m.layerCode;
      layerEl.style.color = LAYER_COLORS[m.layerCode] || '#888';
      document.getElementById('detail-address').textContent = m.address || '주소 없음';
      document.getElementById('detail-id').textContent = m.id;
    }}

    MARKERS_DATA.forEach(m => {{
      const marker = L.marker([m.lat, m.lon], {{ icon: makeIcon(m.layerCode, m.canonical) }});
      marker.bindPopup(
        `<strong>${{m.label}}</strong>` +
        (m.canonical ? ` <span style="color:#FFD700;font-size:11px">★ canonical</span>` : '') +
        `<br><span style="color:${{LAYER_COLORS[m.layerCode]||'#888'}}">${{LAYER_LABELS[m.layerCode]||m.layerCode}}</span>` +
        (m.address ? `<br><small>${{m.address}}</small>` : ''),
        {{ maxWidth: 220 }}
      );
      marker.on('click', () => showDetail(m));
      if (!layerMarkers[m.layerCode]) layerMarkers[m.layerCode] = [];
      layerMarkers[m.layerCode].push(marker);
      clusterGroup.addLayer(marker);
    }});
    map.addLayer(clusterGroup);

    // Layer filter chips
    const chipsEl = document.getElementById('layer-chips');
    Object.entries(LAYER_COLORS).forEach(([code, color]) => {{
      const count = (layerMarkers[code] || []).length;
      if (!count) return;
      const chip = document.createElement('div');
      chip.className = 'layer-chip';
      chip.dataset.code = code;
      chip.innerHTML = `
        <div class="layer-dot" style="background:${{color}}"></div>
        <span class="layer-name">${{LAYER_LABELS[code] || code}}</span>
        <span class="layer-count">${{count.toLocaleString()}}</span>
      `;
      chip.addEventListener('click', () => {{
        const isActive = activeLayerCodes.has(code);
        if (isActive) {{
          activeLayerCodes.delete(code);
          chip.classList.add('off');
          (layerMarkers[code] || []).forEach(m => clusterGroup.removeLayer(m));
        }} else {{
          activeLayerCodes.add(code);
          chip.classList.remove('off');
          (layerMarkers[code] || []).forEach(m => clusterGroup.addLayer(m));
        }}
      }});
      chipsEl.appendChild(chip);
    }});
  </script>
</body>
</html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an interactive HTML viewer for map_view markers.")
    parser.add_argument("--database-url", help="PostgreSQL connection URL.")
    parser.add_argument("--output", type=Path, default=Path("map_markers_view.html"), help="Output HTML file path.")
    parser.add_argument("--no-open", action="store_true", help="Do not auto-open in browser.")
    args = parser.parse_args()

    database_url = resolve_database_url(args.database_url)

    print("DB에서 마커 조회 중...")
    markers = fetch_markers(database_url)
    layer_counts = fetch_layer_counts(database_url)
    print(f"마커 {len(markers):,}개 로드 완료")

    html = build_html(markers, layer_counts)
    output_path = args.output.resolve()
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML 생성: {output_path}")

    if not args.no_open:
        webbrowser.open(output_path.as_uri())
        print("브라우저에서 열림")


if __name__ == "__main__":
    main()
