"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Plug } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OnboardingConnectPage() {
  const router = useRouter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Plug className="h-5 w-5 text-primary" />
          Connect systems
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Link ERP, WMS, TMS or CRM connectors when you&apos;re ready. You can configure these any
          time from Data Sources.
        </p>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Button asChild>
          <Link href="/data-sources/connectors">Browse connectors</Link>
        </Button>
        <Button variant="ghost" onClick={() => router.push("/onboarding/invite")}>
          Skip for now
        </Button>
      </CardContent>
    </Card>
  );
}
