"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OnboardingImportPage() {
  const router = useRouter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Upload className="h-5 w-5 text-primary" />
          Import your data
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Bring in shipments, inventory, warehouses and suppliers via CSV or Excel. You can do this
          later from Data Sources.
        </p>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button asChild>
          <Link href="/data-sources/import">Open CSV import</Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/data-sources/excel">Open Excel import</Link>
        </Button>
        <Button variant="ghost" onClick={() => router.push("/onboarding/connect")}>
          Skip for now
        </Button>
      </CardContent>
    </Card>
  );
}
