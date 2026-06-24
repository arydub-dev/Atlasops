"use client";

import { PageHeader } from "@/components/shared/page-header";
import { ImportCenter } from "@/components/data/import-center";

export default function ExcelImportPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Excel Import Center"
        description="Upload .xlsx workbooks, choose a worksheet, map fields and validate before importing."
      />
      <ImportCenter excel />
    </div>
  );
}
