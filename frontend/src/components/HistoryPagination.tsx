import {
  ChevronLeft,
  ChevronRight
} from "lucide-react";

import type {
  PaginationMeta
} from "../types/api";

interface Props {
  pagination: PaginationMeta;
  onOffsetChange: (
    offset: number
  ) => void;
  disabled?: boolean;
}

export function HistoryPagination({
  pagination,
  onOffsetChange,
  disabled = false
}: Props) {
  const previousOffset =
    Math.max(
      0,
      pagination.offset
      - pagination.limit
    );

  const nextOffset =
    pagination.offset
    + pagination.limit;

  const first =
    pagination.total === 0
      ? 0
      : pagination.offset
        + 1;

  const last =
    Math.min(
      pagination.offset
      + pagination.returned,
      pagination.total
    );

  return (
    <div className="flex items-center justify-between gap-4 border-t border-slate-100 px-5 py-3">
      <p className="text-xs text-slate-400">
        {first}–{last} de{" "}
        {pagination.total}
      </p>

      <div className="flex items-center gap-2">
        <button
          type="button"
          className="btn-secondary !px-3 !py-2"
          disabled={
            disabled
            || pagination.offset
            === 0
          }
          onClick={() =>
            onOffsetChange(
              previousOffset
            )
          }
        >
          <ChevronLeft size={15} />
          Anterior
        </button>

        <button
          type="button"
          className="btn-secondary !px-3 !py-2"
          disabled={
            disabled
            || nextOffset
            >= pagination.total
          }
          onClick={() =>
            onOffsetChange(
              nextOffset
            )
          }
        >
          Próxima
          <ChevronRight size={15} />
        </button>
      </div>
    </div>
  );
}
