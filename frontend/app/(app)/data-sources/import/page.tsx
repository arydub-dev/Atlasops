"use client";

import { PageHeader } from "@/components/shared/page-header";
import { ImportCenter } from "@/components/data/import-center";

export default function CsvImportPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="CSV Import Center"
        description="Upload shipments, inventory, suppliers, warehouses or products — validated and mapped before import."
      />
      <ImportCenter />
    </div>
  );
}
