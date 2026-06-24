"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const AXIS = "hsl(var(--muted-foreground))";
const GRID = "hsl(var(--border))";

const tooltipStyle = {
  backgroundColor: "hsl(var(--popover))",
  border: "1px solid hsl(var(--border))",
  borderRadius: "0.5rem",
  fontSize: "12px",
  color: "hsl(var(--popover-foreground))",
  boxShadow: "0 4px 16px rgb(0 0 0 / 0.2)",
};

const commonAxis = {
  stroke: AXIS,
  fontSize: 11,
  tickLine: false,
  axisLine: false,
};

export interface SeriesDef {
  key: string;
  name: string;
  color: string;
}

interface BaseProps {
  data: Record<string, unknown>[];
  xKey: string;
  series: SeriesDef[];
  height?: number;
  stacked?: boolean;
  showLegend?: boolean;
}

export function AreaTrend({ data, xKey, series, height = 260, showLegend = true }: BaseProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          {series.map((s) => (
            <linearGradient id={`grad-${s.key}`} key={s.key} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={s.color} stopOpacity={0.35} />
              <stop offset="95%" stopColor={s.color} stopOpacity={0} />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={xKey} {...commonAxis} />
        <YAxis {...commonAxis} width={44} />
        <Tooltip contentStyle={tooltipStyle} />
        {showLegend && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {series.map((s) => (
          <Area
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            fill={`url(#grad-${s.key})`}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function BarTrend({ data, xKey, series, height = 260, stacked = false, showLegend = true }: BaseProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={xKey} {...commonAxis} />
        <YAxis {...commonAxis} width={44} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted) / 0.4)" }} />
        {showLegend && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {series.map((s) => (
          <Bar
            key={s.key}
            dataKey={s.key}
            name={s.name}
            fill={s.color}
            radius={stacked ? 0 : [4, 4, 0, 0]}
            stackId={stacked ? "a" : undefined}
            maxBarSize={48}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}

export function LineTrend({ data, xKey, series, height = 260, showLegend = true }: BaseProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
        <XAxis dataKey={xKey} {...commonAxis} />
        <YAxis {...commonAxis} width={44} />
        <Tooltip contentStyle={tooltipStyle} />
        {showLegend && <Legend wrapperStyle={{ fontSize: 11 }} />}
        {series.map((s) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.name}
            stroke={s.color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

interface DonutProps {
  data: { name: string; value: number; color: string }[];
  height?: number;
  innerRadius?: number;
}

export function Donut({ data, height = 240, innerRadius = 56 }: DonutProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={innerRadius}
          outerRadius={innerRadius + 28}
          paddingAngle={2}
          stroke="hsl(var(--card))"
          strokeWidth={2}
        >
          {data.map((d) => (
            <Cell key={d.name} fill={d.color} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
        <Legend wrapperStyle={{ fontSize: 11 }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

interface HBarProps {
  data: { name: string; value: number }[];
  height?: number;
  color?: string;
  unit?: string;
}

export function HorizontalBars({ data, height = 280, color = "#3b82f6" }: HBarProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
        <XAxis type="number" {...commonAxis} />
        <YAxis type="category" dataKey="name" {...commonAxis} width={130} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "hsl(var(--muted) / 0.4)" }} />
        <Bar dataKey="value" fill={color} radius={[0, 4, 4, 0]} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  );
}
