import { useMemo, useState } from 'react';

export function DataTable({ columns, data, onRowClick, selectedIds = [], onSelectAll, onSelectRow }) {
  const [sort, setSort] = useState(null);
  const sortedData = useMemo(() => {
    if (!sort) return data;
    const column = columns.find((item) => item.header === sort.header);
    if (!column?.accessor) return data;
    return [...data].sort((a, b) => {
      const left = a[column.accessor];
      const right = b[column.accessor];
      const result = typeof left === 'number' && typeof right === 'number'
        ? left - right
        : String(left ?? '').localeCompare(String(right ?? ''), undefined, { numeric: true, sensitivity: 'base' });
      return sort.direction === 'asc' ? result : -result;
    });
  }, [columns, data, sort]);
  const hasSelection = Boolean(onSelectRow);

  return (
    <div className="overflow-x-auto rounded-lg border border-[#1e2638] bg-[#0f131c]">
      <table className="w-full text-left text-sm text-slate-300">
        <thead className="bg-[#181c24] text-xs uppercase tracking-wider text-slate-400 border-b border-[#1e2638]">
          <tr>
            {hasSelection && (
              <th className="p-3.5 w-10 text-center">
                <input
                  aria-label="Select all rows"
                  type="checkbox"
                  className="rounded border-slate-700 bg-slate-900 text-blue-600 focus:ring-blue-500/20"
                  onChange={(e) => onSelectAll?.(e.target.checked)}
                  checked={data.length > 0 && data.every((row) => selectedIds.includes(row.id))}
                  ref={(node) => { if (node) node.indeterminate = data.some((row) => selectedIds.includes(row.id)) && !data.every((row) => selectedIds.includes(row.id)); }}
                />
              </th>
            )}
            {columns.map((col, idx) => (
                <th key={idx} scope="col" aria-sort={sort?.header === col.header ? (sort.direction === 'asc' ? 'ascending' : 'descending') : undefined} className={`p-3.5 font-semibold ${col.className || ''}`}>
                {col.accessor ? <button type="button" className="inline-flex items-center gap-1 hover:text-white" onClick={() => setSort((current) => current?.header === col.header ? { header: col.header, direction: current.direction === 'asc' ? 'desc' : 'asc' } : { header: col.header, direction: 'asc' })} aria-label={`Sort by ${col.header}`}>
                  {col.header}{sort?.header === col.header ? (sort.direction === 'asc' ? ' ↑' : ' ↓') : ''}
                </button> : col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#1e2638]">
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length + (hasSelection ? 1 : 0)} className="text-center py-8 text-slate-500">
                No matching records found
              </td>
            </tr>
          ) : (
            sortedData.map((row, rowIdx) => {
              const isSelected = selectedIds.includes(row.id);
              return (
                <tr
                  key={row.id || rowIdx}
                  onClick={(event) => { if (onRowClick) { event.currentTarget.focus(); onRowClick(row); } }}
                  onKeyDown={(event) => { if (onRowClick && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onRowClick(row); } }}
                  tabIndex={onRowClick ? 0 : undefined}
                  aria-label={onRowClick ? `Open ${row.id || 'row'}` : undefined}
                  className={`${onRowClick ? 'cursor-pointer' : ''} hover:bg-[#181c24]/70 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-500 transition-colors ${isSelected ? 'bg-blue-900/10' : ''}`}
                >
                  {hasSelection && (
                    <td className="p-3.5 text-center" onClick={(e) => e.stopPropagation()}>
                      <input
                        aria-label={`Select ${row.id}`}
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onSelectRow?.(row.id)}
                        className="rounded border-slate-700 bg-slate-900 text-blue-600 focus:ring-blue-500/20"
                      />
                    </td>
                  )}
                  {columns.map((col, cIdx) => (
                    <td key={cIdx} className={`p-3.5 ${col.cellClassName || ''}`}>
                      {col.render ? col.render(row) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}
