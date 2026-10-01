import type { Metadata } from "next";
export const metadata: Metadata = { title: 'Supply Chain Platform', description: 'Explore a unified workspace for shipment visibility, supplier risk, inventory intelligence and operational decisions.', alternates: {canonical: "/platform"} };
export default function Layout({children}: {children: React.ReactNode}) { return children; }
