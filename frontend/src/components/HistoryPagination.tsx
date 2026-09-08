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

  const currentPage =
    pagination.total === 0
      ? 0
      : Math.floor(
          pagination.offset
          / pagination.limit
        ) + 1;

  const totalPages =
    pagination.total === 0
      ? 0
      : Math.ceil(
          pagination.total
          / pagination.limit
        );

  return (
    <nav aria-label="Paginação do histórico" className="flex flex-col gap-3 border-t border-[#edf0f7] bg-[#fafbfe] px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5">
      <div>
        <p className="text-xs font-medium text-[#616981]">
          {first}–{last} de {pagination.total}
        </p>
        <p className="mt-0.5 text-[10px] font-medium uppercase tracking-[0.12em] text-[#a0a6b8]">
          Página {currentPage} de {totalPages}
        </p>
      </div>

      <div className="flex items-center gap-2 max-[440px]:grid max-[440px]:grid-cols-2">
        <button
          type="button"
          aria-label="Página anterior"
          className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-xl border border-[#e2e5ee] bg-white px-3 text-xs font-semibold text-[#59617b] shadow-[0_3px_10px_rgba(34,39,76,0.035)] transition hover:border-[#d3d8e8] hover:text-[#303778] disabled:cursor-not-allowed disabled:opacity-40"
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
          <ChevronLeft size={14} />
          Anterior
        </button>

        <button
          type="button"
          aria-label="Próxima página"
          className="inline-flex min-h-9 items-center justify-center gap-1.5 rounded-xl border border-[#e2e5ee] bg-white px-3 text-xs font-semibold text-[#59617b] shadow-[0_3px_10px_rgba(34,39,76,0.035)] transition hover:border-[#d3d8e8] hover:text-[#303778] disabled:cursor-not-allowed disabled:opacity-40"
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
          <ChevronRight size={14} />
        </button>
      </div>
    </nav>
  );
}
