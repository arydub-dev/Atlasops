/**
 * World landmass geometry for the Network View map.
 *
 * Converts the bundled Natural Earth (110m) TopoJSON country borders into
 * plain GeoJSON features once at module load. Consumers project the raw
 * [lon, lat] coordinates themselves so the landmasses stay perfectly aligned
 * with node positions regardless of the projection used.
 */
import { feature } from "topojson-client";
import worldTopo from "world-atlas/countries-110m.json";

export type LonLat = [number, number];

export type LandGeometry =
  | { type: "Polygon"; coordinates: LonLat[][] }
  | { type: "MultiPolygon"; coordinates: LonLat[][][] };

// topojson-client / world-atlas typings are intentionally loose here.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const topo = worldTopo as any;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const collection = feature(topo, topo.objects.countries) as any;

export const WORLD_FEATURES: { geometry: LandGeometry | null }[] =
  collection.features ?? [];
