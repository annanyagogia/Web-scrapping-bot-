import { Check, Plus } from "lucide-react";
import { cn } from "../lib/utils";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

export function FieldPicker({ fields, selected, onChange, customField, onCustomFieldChange, onAddCustomField }) {
  const selectedSet = new Set(selected);

  function toggle(field) {
    if (selectedSet.has(field)) {
      onChange(selected.filter((item) => item !== field));
      return;
    }
    onChange([...selected, field]);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {fields.map((field) => (
          <button
            key={field}
            type="button"
            onClick={() => toggle(field)}
            className={cn(
              "inline-flex h-9 items-center gap-2 rounded-md border px-3 text-sm transition",
              selectedSet.has(field)
                ? "border-sky-300/50 bg-sky-400/16 text-sky-100"
                : "border-border bg-slate-950/40 text-slate-300 hover:bg-white/8"
            )}
          >
            {selectedSet.has(field) ? <Check size={14} /> : null}
            {field}
          </button>
        ))}
      </div>
      <div className="flex gap-2">
        <Input
          value={customField}
          onChange={(event) => onCustomFieldChange(event.target.value)}
          placeholder="custom_field"
        />
        <Button variant="secondary" size="icon" onClick={onAddCustomField} title="Add custom field">
          <Plus size={17} />
        </Button>
      </div>
    </div>
  );
}
