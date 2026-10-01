"use client";

import { useEffect, useRef } from "react";
import type { NetworkData, NetworkNode } from "@/lib/types";

function riskColor(score: number): string {
  if (score >= 70) return "#ef4444";
  if (score >= 45) return "#f59e0b";
  return "#22c55e";
}

export function NetworkMapbox({
  data,
  token,
  selected,
  onSelect,
  showSuppliers,
  showRoutes,
}: {
  data: NetworkData;
  token: string;
  selected: NetworkNode | null;
  onSelect: (n: NetworkNode | null) => void;
  showSuppliers: boolean;
  showRoutes: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<import("mapbox-gl").Map | null>(null);

  useEffect(() => {
    let cancelled = false;
    let map: import("mapbox-gl").Map | null = null;

    async function boot() {
      const mapboxgl = (await import("mapbox-gl")).default;
      await import("mapbox-gl/dist/mapbox-gl.css");
      if (cancelled || !containerRef.current) return;

      mapboxgl.accessToken = token;
      map = new mapboxgl.Map({
        container: containerRef.current,
        style: "mapbox://styles/mapbox/dark-v11",
        center: [10, 25],
        zoom: 1.4,
        attributionControl: true,
      });
      map.addControl(new mapboxgl.NavigationControl({ visualizePitch: false }), "top-right");
      mapRef.current = map;

      map.on("load", () => {
        if (!map) return;
        const nodes = showSuppliers
          ? data.nodes
          : data.nodes.filter((n) => n.type === "warehouse");

        const features = nodes.map((n) => ({
          type: "Feature" as const,
          properties: {
            id: n.id,
            name: n.name,
            type: n.type,
            risk_score: n.risk_score,
            entity_id: n.entity_id,
          },
          geometry: {
            type: "Point" as const,
            coordinates: [n.lon, n.lat],
          },
        }));

        map.addSource("nodes", {
          type: "geojson",
          data: { type: "FeatureCollection", features },
        });

        map.addLayer({
          id: "nodes-circle",
          type: "circle",
          source: "nodes",
          paint: {
            "circle-radius": ["case", ["==", ["get", "type"], "warehouse"], 8, 6],
            "circle-color": [
              "case",
              [">=", ["get", "risk_score"], 70],
              "#ef4444",
              [">=", ["get", "risk_score"], 45],
              "#f59e0b",
              "#22c55e",
            ],
            "circle-stroke-width": 1.5,
            "circle-stroke-color": "#0f172a",
          },
        });

        map.addLayer({
          id: "nodes-label",
          type: "symbol",
          source: "nodes",
          layout: {
            "text-field": ["get", "name"],
            "text-size": 11,
            "text-offset": [0, 1.2],
            "text-anchor": "top",
          },
          paint: {
            "text-color": "#e2e8f0",
            "text-halo-color": "#0f172a",
            "text-halo-width": 1,
          },
        });

        if (showRoutes && data.edges.length) {
          const lineFeatures = data.edges.map((e) => ({
            type: "Feature" as const,
            properties: {
              delay_rate: e.delay_rate,
              volume: e.volume,
            },
            geometry: {
              type: "LineString" as const,
              coordinates: [
                [e.from.lon, e.from.lat],
                [e.to.lon, e.to.lat],
              ],
            },
          }));
          map.addSource("routes", {
            type: "geojson",
            data: { type: "FeatureCollection", features: lineFeatures },
          });
          map.addLayer(
            {
              id: "routes-line",
              type: "line",
              source: "routes",
              paint: {
                "line-width": ["interpolate", ["linear"], ["get", "volume"], 1, 1, 50, 4],
                "line-color": [
                  "case",
                  [">=", ["get", "delay_rate"], 40],
                  "#ef4444",
                  [">=", ["get", "delay_rate"], 20],
                  "#f59e0b",
                  "#22c55e",
                ],
                "line-opacity": 0.65,
              },
            },
            "nodes-circle"
          );
        }

        map.on("click", "nodes-circle", (ev) => {
          const f = ev.features?.[0];
          if (!f?.properties) return;
          const node = data.nodes.find((n) => n.id === f.properties!.id);
          onSelect(node || null);
        });
        map.on("mouseenter", "nodes-circle", () => {
          map!.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "nodes-circle", () => {
          map!.getCanvas().style.cursor = "";
        });
      });
    }

    boot();
    return () => {
      cancelled = true;
      map?.remove();
      mapRef.current = null;
    };
    // Re-init when filters/data change
  }, [data, token, showSuppliers, showRoutes, onSelect]);

  useEffect(() => {
    // Highlight selection via popup-less visual is handled by parent panel.
    void selected;
    void riskColor;
  }, [selected]);

  return <div ref={containerRef} className="h-full min-h-[420px] w-full rounded-lg" />;
}
