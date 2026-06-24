import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { formatNumber } from "@/lib/format";

interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}

export function Pagination({ page, pages, total, onPage }: PaginationProps) {
  return (
    <div className="flex items-center justify-between gap-3 pt-1 text-sm">
      <p className="text-xs text-muted-foreground">
        Page {page} of {Math.max(pages, 1)} · {formatNumber(total)} records
      </p>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          <ChevronLeft className="h-4 w-4" />
          Prev
        </Button>
        <Button
          variant="outline"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
        >
          Next
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
