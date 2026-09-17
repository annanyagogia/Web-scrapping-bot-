import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  useReactTable
} from "@tanstack/react-table";
import { Download, Search } from "lucide-react";
import { useMemo, useState } from "react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Input } from "../components/ui/input";
import { uniqueFields } from "../lib/utils";

export function ResultsTablePage({ scrapeResult, onExport }) {
  const [globalFilter, setGlobalFilter] = useState("");
  const records = scrapeResult?.data || [];
  const columns = useMemo(
    () =>
      uniqueFields(records).map((field) => ({
        accessorKey: field,
        header: field,
        cell: ({ getValue }) => {
          const value = getValue();
          if (Array.isArray(value)) return value.join(", ");
          if (typeof value === "object" && value !== null) return JSON.stringify(value);
          return String(value ?? "");
        }
      })),
    [records]
  );

  const table = useReactTable({
    data: records,
    columns,
    state: { globalFilter },
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel()
  });

  return (
    <div className="space-y-6">
      <section>
        <p className="text-sm text-sky-200">Results Table</p>
        <h1 className="mt-2 text-2xl font-semibold text-white">Preview extracted records</h1>
      </section>

      <Card>
        <CardHeader>
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle>{records.length} records</CardTitle>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative">
                <Search size={16} className="absolute left-3 top-3 text-slate-500" />
                <Input
                  value={globalFilter}
                  onChange={(event) => setGlobalFilter(event.target.value)}
                  placeholder="Filter rows"
                  className="pl-9"
                />
              </div>
              <Button variant="secondary" disabled={!records.length} onClick={() => onExport("csv")}>
                <Download size={16} />
                CSV
              </Button>
              <Button variant="secondary" disabled={!records.length} onClick={() => onExport("excel")}>
                <Download size={16} />
                Excel
              </Button>
              <Button variant="secondary" disabled={!records.length} onClick={() => onExport("json")}>
                <Download size={16} />
                JSON
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="overflow-hidden rounded-md border border-border">
            <div className="max-h-[35rem] overflow-auto">
              <table className="min-w-full border-collapse text-sm">
                <thead className="sticky top-0 bg-slate-950">
                  {table.getHeaderGroups().map((headerGroup) => (
                    <tr key={headerGroup.id}>
                      {headerGroup.headers.map((header) => (
                        <th key={header.id} className="border-b border-border px-3 py-3 text-left text-xs font-medium uppercase text-slate-400">
                          {flexRender(header.column.columnDef.header, header.getContext())}
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="border-b border-border/70 hover:bg-white/5">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="max-w-72 px-3 py-3 text-slate-200">
                          <span className="line-clamp-3 break-words">{flexRender(cell.column.columnDef.cell, cell.getContext())}</span>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!records.length ? <div className="p-8 text-center text-sm text-slate-400">No results yet.</div> : null}
          </div>

          {records.length ? (
            <div className="mt-4 flex items-center justify-between gap-3 text-sm text-slate-400">
              <Button variant="ghost" size="sm" disabled={!table.getCanPreviousPage()} onClick={() => table.previousPage()}>
                Previous
              </Button>
              <span>
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
              </span>
              <Button variant="ghost" size="sm" disabled={!table.getCanNextPage()} onClick={() => table.nextPage()}>
                Next
              </Button>
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
