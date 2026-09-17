import { MousePointer2, Wand2 } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

const DEFAULT_SELECTOR_FIELDS = ["product_name", "price", "image_url", "product_url"];

export function ManualSelectorMode({ selectors, onChange, onApply, selectedFields }) {
  const fields = selectedFields.length ? selectedFields : DEFAULT_SELECTOR_FIELDS;

  function setSelector(field, value) {
    onChange({ ...selectors, [field]: value });
  }

  return (
    <section className="rounded-panel border border-border bg-slate-950/35 p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium text-slate-100">
          <MousePointer2 size={16} className="text-sky-300" />
          Manual selector mode
        </div>
        <Button size="sm" variant="secondary" onClick={onApply}>
          <Wand2 size={15} />
          Train
        </Button>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {fields.map((field) => (
          <label key={field} className="space-y-1.5">
            <span className="text-xs text-slate-400">{field}</span>
            <Input
              value={selectors[field] || ""}
              onChange={(event) => setSelector(field, event.target.value)}
              placeholder={field === "price" ? ".price" : `[data-field="${field}"]`}
            />
          </label>
        ))}
      </div>
    </section>
  );
}
