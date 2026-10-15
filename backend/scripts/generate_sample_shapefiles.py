"""
Generate realistic InfoWorks ICM 2D flood inundation contour Shapefiles
for the Kuching, Sarawak drain network (Drain 46 & Drain 53).

Creates hourly shapefile batches:
  FloodContours_260826_1000.* through FloodContours_260826_1800.*
plus a peak-envelope batch: FloodContours_260826_Maxima.*
in data/exports/ with .shp, .shx, .dbf, and .prj in Sarawak RSO (EPSG:29873).
"""

from __future__ import annotations

import math
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import rotate, scale, translate

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXPORTS_DIR = BASE_DIR / "data" / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Kuching Sarawak drain network anchors (WGS84)
# Drain 46: 1.5535 N, 110.3485 E
# Drain 53: 1.5590 N, 110.3440 E
CENTER_LON = 110.3465
CENTER_LAT = 1.5560

from typing import TypedDict


class HourlyFrame(TypedDict):
    ts: str
    scale: float
    depth_min: float
    depth_max: float
    elev_base: float


class DepthTier(TypedDict):
    tier: int
    label: str
    depth_mult: float
    elev_delta: float


HOURLY_FRAMES: list[HourlyFrame] = [
    {"ts": "1000", "scale": 0.45, "depth_min": 0.15, "depth_max": 0.50, "elev_base": 2.1},
    {"ts": "1100", "scale": 0.70, "depth_min": 0.25, "depth_max": 0.85, "elev_base": 2.4},
    {"ts": "1200", "scale": 1.05, "depth_min": 0.40, "depth_max": 1.30, "elev_base": 2.8},
    {"ts": "1300", "scale": 1.45, "depth_min": 0.65, "depth_max": 1.85, "elev_base": 3.3},
    {"ts": "1400", "scale": 1.80, "depth_min": 0.90, "depth_max": 2.45, "elev_base": 3.8},  # Peak
    {"ts": "1500", "scale": 1.65, "depth_min": 0.80, "depth_max": 2.25, "elev_base": 3.6},
    {"ts": "1600", "scale": 1.30, "depth_min": 0.55, "depth_max": 1.70, "elev_base": 3.1},
    {"ts": "1700", "scale": 0.90, "depth_min": 0.35, "depth_max": 1.15, "elev_base": 2.6},
    {"ts": "1800", "scale": 0.55, "depth_min": 0.20, "depth_max": 0.65, "elev_base": 2.2},
]
PEAK_FRAME = max(HOURLY_FRAMES, key=lambda frame: frame["scale"])


def make_curved_corridor(base_lon: float, base_lat: float, scale_factor: float, depth_tier: int):
    """Generate irregular polygon rings representing flood depth contours along the river/drain."""
    points = []
    num_pts = 24
    rx = 0.0035 * scale_factor * (1.0 - depth_tier * 0.18)
    ry = 0.0022 * scale_factor * (1.0 - depth_tier * 0.18)

    # Base meandering shape
    for i in range(num_pts):
        angle = (2 * math.pi * i) / num_pts
        # Add natural perturbations
        wobble = 0.18 * math.sin(3 * angle) + 0.12 * math.cos(5 * angle)
        r_actual_x = rx * (1 + wobble)
        r_actual_y = ry * (1 + wobble)
        x = base_lon + r_actual_x * math.cos(angle)
        y = base_lat + r_actual_y * math.sin(angle)
        points.append((x, y))

    points.append(points[0])  # close ring
    poly = Polygon(points)
    # Tilt slightly to match the Sungai Sarawak / Padungan flow angle (-25 deg)
    return rotate(poly, -25, origin=(base_lon, base_lat))  # type: ignore[arg-type]


def make_tributary_ponding(base_lon: float, base_lat: float, scale_factor: float, depth_tier: int):
    """Secondary inundation pooling area near urban lowlands."""
    points = []
    num_pts = 16
    rx = 0.0018 * scale_factor * (1.0 - depth_tier * 0.2)
    ry = 0.0014 * scale_factor * (1.0 - depth_tier * 0.2)

    for i in range(num_pts):
        angle = (2 * math.pi * i) / num_pts
        wobble = 0.15 * math.cos(4 * angle)
        x = base_lon + rx * (1 + wobble) * math.cos(angle)
        y = base_lat + ry * (1 + wobble) * math.sin(angle)
        points.append((x, y))

    points.append(points[0])
    return Polygon(points)


def generate_hourly_shapefiles():
    """Build and write the shapefile batches to data/exports/."""
    print(f"Generating realistic InfoWorks ICM Shapefiles in {EXPORTS_DIR}...")
    peak_features: list[dict[str, object]] = []

    for frame in HOURLY_FRAMES:
        ts = frame["ts"]
        s = frame["scale"]
        base_depth_min = frame["depth_min"]
        base_depth_max = frame["depth_max"]
        elev_base = frame["elev_base"]

        features: list[dict[str, object]] = []

        # Generate 3 depth zones per frame:
        # Zone 0: Outer perimeter (shallowest: e.g. 0.15 - 0.50m)
        # Zone 1: Moderate inundation (0.50 - 1.20m)
        # Zone 2: Deep channel/depressions (> 1.20m)
        depth_tiers: list[DepthTier] = [
            {"tier": 0, "label": "Shallow Inundation", "depth_mult": 0.35, "elev_delta": 0.2},
            {"tier": 1, "label": "Moderate Inundation", "depth_mult": 0.65, "elev_delta": 0.6},
            {"tier": 2, "label": "Severe Inundation", "depth_mult": 1.00, "elev_delta": 1.1},
        ]

        for dt in depth_tiers:
            tier_idx = dt["tier"]
            # Main channel corridor
            poly1 = make_curved_corridor(CENTER_LON, CENTER_LAT, s, tier_idx)
            # Padungan tributary pocket
            poly2 = make_tributary_ponding(CENTER_LON + 0.0035, CENTER_LAT - 0.0020, s * 0.85, tier_idx)

            depth_val = round(base_depth_min + (base_depth_max - base_depth_min) * dt["depth_mult"], 3)
            elev_val = round(elev_base + dt["elev_delta"], 3)

            features.append({
                "geometry": poly1,
                "Zone": dt["label"],
                "Depth": depth_val,
                "Elevation": elev_val,
                "MaxDepth": depth_val,
                "Hazard": "HIGH" if depth_val > 1.2 else "MEDIUM" if depth_val > 0.5 else "LOW",
                "Timestep": ts,
            })

            features.append({
                "geometry": poly2,
                "Zone": f"{dt['label']} (Tributary)",
                "Depth": round(depth_val * 0.85, 3),
                "Elevation": round(elev_val - 0.1, 3),
                "MaxDepth": round(depth_val * 0.85, 3),
                "Hazard": "HIGH" if depth_val * 0.85 > 1.2 else "MEDIUM" if depth_val * 0.85 > 0.5 else "LOW",
                "Timestep": ts,
            })

        if ts == PEAK_FRAME["ts"]:
            peak_features = [
                {**feature, "Timestep": "Maxima"}
                for feature in features
            ]

        # Create GeoDataFrame in WGS84
        gdf_wgs84 = gpd.GeoDataFrame.from_features(
            [
                {
                    "geometry": feature["geometry"],
                    "properties": {
                        key: value
                        for key, value in feature.items()
                        if key != "geometry"
                    },
                }
                for feature in features
            ],
            crs="EPSG:4326",
        )

        # Project to local Sarawak RSO (EPSG:29873) to faithfully mirror actual ICM exports
        gdf_rso = gdf_wgs84.to_crs("EPSG:29873")

        out_name = f"FloodContours_260826_{ts}"
        shp_path = EXPORTS_DIR / f"{out_name}.shp"

        # Save shapefile with .shp, .shx, .dbf, .prj
        gdf_rso.to_file(shp_path, driver="ESRI Shapefile")
        print(f" -> Created: {shp_path.name} (CRS: EPSG:29873 Sarawak RSO, {len(features)} polygons)")

    if peak_features:
        maxima_gdf = gpd.GeoDataFrame.from_features(
            [
                {
                    "geometry": feature["geometry"],
                    "properties": {
                        key: value
                        for key, value in feature.items()
                        if key != "geometry"
                    },
                }
                for feature in peak_features
            ],
            crs="EPSG:4326",
        ).to_crs("EPSG:29873")
        maxima_path = EXPORTS_DIR / "FloodContours_260826_Maxima.shp"
        maxima_gdf.to_file(maxima_path, driver="ESRI Shapefile")
        print(f" -> Created: {maxima_path.name} (peak frame {PEAK_FRAME['ts']}, {len(peak_features)} polygons)")

    print("All sample Shapefiles generated successfully!")


if __name__ == "__main__":
    generate_hourly_shapefiles()
