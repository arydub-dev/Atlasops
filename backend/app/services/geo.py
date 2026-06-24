"""Geographic reference data for the Supply Chain Network View.

Maps the city names used across the dataset to approximate lat/long, and
provides regional centroids for placing suppliers on the map.
"""
from __future__ import annotations

CITY_COORDS: dict[str, tuple[float, float]] = {
    "Los Angeles": (34.05, -118.24),
    "Newark": (40.73, -74.17),
    "Chicago": (41.88, -87.63),
    "Rotterdam": (51.92, 4.48),
    "Hamburg": (53.55, 9.99),
    "Shanghai": (31.23, 121.47),
    "Shenzhen": (22.54, 114.06),
    "Singapore": (1.35, 103.82),
    "Mumbai": (19.08, 72.88),
    "Dubai": (25.20, 55.27),
    "Sao Paulo": (-23.55, -46.63),
    "Tokyo": (35.68, 139.69),
    "Busan": (35.18, 129.08),
    "Antwerp": (51.22, 4.40),
    "Houston": (29.76, -95.37),
    "Atlanta": (33.75, -84.39),
    "Memphis": (35.15, -90.05),
    "Dallas": (32.78, -96.80),
    "Felixstowe": (51.96, 1.35),
    "Gdansk": (54.35, 18.65),
    "Veracruz": (19.17, -96.13),
    "Santos": (-23.96, -46.33),
    "Jebel Ali": (25.01, 55.06),
    "Kaohsiung": (22.62, 120.27),
    "Ho Chi Minh City": (10.82, 106.63),
}

REGION_CENTROIDS: dict[str, tuple[float, float]] = {
    "North America": (39.0, -98.0),
    "Europe": (50.5, 9.0),
    "APAC": (24.0, 113.0),
    "LATAM": (-15.0, -55.0),
    "Middle East": (25.5, 51.0),
    "Africa": (2.0, 21.0),
}


def city_coords(name: str) -> tuple[float, float] | None:
    if name in CITY_COORDS:
        return CITY_COORDS[name]
    # tolerant match (e.g. "Chicago DC-01" -> "Chicago")
    for city, coords in CITY_COORDS.items():
        if name.startswith(city):
            return coords
    return None


def region_centroid(region: str) -> tuple[float, float]:
    return REGION_CENTROIDS.get(region, (20.0, 0.0))


def jitter(seed: int, scale: float = 6.0) -> tuple[float, float]:
    """Deterministic small offset so co-located nodes don't overlap."""
    a = ((seed * 53) % 100) / 100 - 0.5
    b = ((seed * 97) % 100) / 100 - 0.5
    return (a * scale, b * scale)
