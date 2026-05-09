"use client";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { useState, useMemo } from "react";
import { ArrowUpDown } from "lucide-react";
import { cn, formatNumber } from "@/lib/utils";
import type { ResultsPreview } from "@/types";

interface ResultsTableProps {
  results: ResultsPreview;
  rowCount: number;
}

export function ResultsTable({ results, rowCount }: ResultsTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(
    () =>
      results.columns.map((col) => ({
        accessorKey: col,
        header: ({ column }) => (
          <button
            className="flex items-center gap-1 text-xs font-semibold uppercase tracking-wider hover:text-foreground"
            onClick={() => column.toggleSorting(column.getIsSorted() === "asc")}
          >
            {col}
            <ArrowUpDown className="h-3 w-3 opacity-50" />
          </button>
        ),
        cell: ({ getValue }) => {
          const val = getValue();
          return (
            <span className="text-sm">
              {val === null || val === undefined
                ? <span className="text-muted-foreground italic">null</span>
                : String(val)}
            </span>
          );
        },
      })),
    [results.columns],
  );

  const data = useMemo(
    () =>
      results.rows.map((row) => {
        const obj: Record<string, unknown> = {};
        results.columns.forEach((col, i) => { obj[col] = (row as unknown[])[i]; });
        return obj;
      }),
    [results.rows, results.columns],
  );

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="rounded-md border">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="border-b bg-muted/30">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th key={header.id} className="px-3 py-2 text-muted-foreground">
                    {flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row, i) => (
              <tr
                key={row.id}
                className={cn("border-b last:border-0", i % 2 === 0 ? "bg-background" : "bg-muted/10")}
              >
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="px-3 py-1.5 font-mono">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-between border-t px-3 py-2">
        <span className="text-xs text-muted-foreground">
          Showing {results.rows.length} of {formatNumber(rowCount)} row{rowCount !== 1 ? "s" : ""}
        </span>
        {rowCount > results.rows.length && (
          <span className="text-xs text-amber-600">
            Preview limited to {results.rows.length} rows
          </span>
        )}
      </div>
    </div>
  );
}
