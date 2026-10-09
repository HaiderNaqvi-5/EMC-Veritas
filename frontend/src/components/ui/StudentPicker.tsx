import { useId, useMemo, useRef, useState } from "react";

type Student = {
  id: string;
  roll_number: string;
  full_name: string;
  active: boolean;
};

type StudentPickerProps = {
  students: Student[];
  value: string;
  onChange: (studentId: string) => void;
  disabled?: boolean;
  label?: string;
};

export function StudentPicker({
  students,
  value,
  onChange,
  disabled = false,
  label = "Eligible student",
}: StudentPickerProps) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const instanceId = useId();
  const inputId = `student-picker-${instanceId}`;
  const optionsId = `student-picker-options-${instanceId}`;
  const activeStudents = useMemo(
    () => students.filter((student) => student.active),
    [students],
  );
  const matches = useMemo(() => {
    const term = search.trim().toLowerCase();
    return term
      ? activeStudents.filter((student) =>
          `${student.roll_number} ${student.full_name}`.toLowerCase().includes(term),
        )
      : activeStudents;
  }, [activeStudents, search]);
  const selected = activeStudents.find((student) => student.id === value);

  function choose(student: Student) {
    onChange(student.id);
    setSearch("");
    setOpen(false);
    inputRef.current?.focus();
  }

  return (
    <div className="relative">
      <label className="sr-only" htmlFor={inputId}>
        {label}
      </label>
      <input
        id={inputId}
        ref={inputRef}
        type="text"
        role="combobox"
        aria-label={label}
        aria-autocomplete="list"
        aria-expanded={open}
        aria-controls={optionsId}
        aria-activedescendant={
          open && matches[activeIndex]
            ? `${optionsId}-${matches[activeIndex].id}`
            : undefined
        }
        disabled={disabled}
        value={search}
        placeholder={
          selected
            ? `${selected.roll_number} — ${selected.full_name}`
            : "Search active students"
        }
        onFocus={() => setOpen(true)}
        onChange={(event) => {
          setSearch(event.target.value);
          setActiveIndex(0);
          setOpen(true);
        }}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setOpen(true);
            setActiveIndex((index) =>
              Math.min(index + 1, Math.max(matches.length - 1, 0)),
            );
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setActiveIndex((index) => Math.max(index - 1, 0));
          }
          if (event.key === "Enter" && open && matches[activeIndex]) {
            event.preventDefault();
            choose(matches[activeIndex]);
          }
          if (event.key === "Escape") setOpen(false);
        }}
        className="w-full rounded-lg border border-slate-300 bg-white p-2.5 text-sm outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/30 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-950"
      />
      {value && (
        <button
          type="button"
          onClick={() => onChange("")}
          disabled={disabled}
          className="mt-1 text-xs text-slate-500 underline focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          Clear selected student
        </button>
      )}
      {open && !disabled && (
        <ul
          id={optionsId}
          role="listbox"
          aria-label="Active students"
          className="absolute z-20 mt-1 max-h-56 w-full overflow-y-auto rounded-lg border border-slate-200 bg-white p-1 shadow-lg dark:border-slate-700 dark:bg-slate-900"
        >
          {matches.length ? (
            matches.map((student, index) => (
              <li
                key={student.id}
                id={`${optionsId}-${student.id}`}
                role="option"
                aria-selected={student.id === value}
              >
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => choose(student)}
                  className={`w-full rounded px-3 py-2 text-left text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 ${index === activeIndex ? "bg-indigo-50 text-indigo-950 dark:bg-indigo-950 dark:text-indigo-50" : "hover:bg-slate-100 dark:hover:bg-slate-800"}`}
                >
                  <span className="font-medium">{student.roll_number}</span>
                  <span className="text-slate-500"> — {student.full_name}</span>
                </button>
              </li>
            ))
          ) : (
            <li className="px-3 py-3 text-sm text-slate-500">
              No active students match this search.
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
