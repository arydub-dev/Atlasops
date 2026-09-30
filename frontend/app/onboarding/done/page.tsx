"use client";

import { useRouter } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function OnboardingDonePage() {
  const router = useRouter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <CheckCircle2 className="h-5 w-5 text-primary" />
          You&apos;re ready
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Your Supply workspace is set up. Head to Mission Control to start operating.
        </p>
      </CardHeader>
      <CardContent>
        <Button onClick={() => router.push("/mission-control")}>Go to Mission Control</Button>
      </CardContent>
    </Card>
  );
}
