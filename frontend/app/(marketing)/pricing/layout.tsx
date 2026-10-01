import type { Metadata } from "next";
export const metadata: Metadata = { title: 'Plans and Pricing', description: 'Compare ATLASOPS plans and connect with our team about enterprise requirements.', alternates: {canonical: "/pricing"} };
export default function Layout({children}: {children: React.ReactNode}) { return children; }
