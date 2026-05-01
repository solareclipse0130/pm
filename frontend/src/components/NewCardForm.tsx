import { useState, type FormEvent } from "react";

const initialFormState = { title: "", details: "" };

type NewCardFormProps = {
  accentColor?: string;
  onAdd: (title: string, details: string) => void;
};

export const NewCardForm = ({
  accentColor = "var(--pacific-blue)",
  onAdd,
}: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(formState.title.trim(), formState.details.trim());
    setFormState(initialFormState);
    setIsOpen(false);
  };

  return (
    <div className="relative mt-4">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            className="focus-ring w-full rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm font-semibold text-[var(--deep-sea)] outline-none placeholder:font-medium placeholder:text-[var(--slate)]"
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            rows={3}
            className="focus-ring w-full resize-none rounded-xl border border-[var(--stroke)] bg-white px-3 py-2 text-sm leading-6 text-[var(--slate)] outline-none placeholder:text-[var(--slate)]"
          />
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="focus-ring rounded-full px-3.5 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-white transition hover:brightness-110"
              style={{
                background:
                  "linear-gradient(135deg, var(--pacific-blue), var(--aqua-mist))",
                boxShadow: "0 8px 18px rgba(123, 196, 188, 0.22)",
              }}
            >
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              className="focus-ring rounded-full border border-[var(--stroke)] px-3 py-2 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--slate)] transition hover:border-[var(--stroke-strong)] hover:text-[var(--deep-sea)]"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="focus-ring group/add flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-[var(--stroke)] bg-white/60 px-3 py-2.5 text-xs font-semibold uppercase tracking-[0.16em] transition hover:bg-white"
          style={{ color: accentColor, borderColor: "var(--stroke)" }}
        >
          <span
            aria-hidden
            className="inline-flex h-5 w-5 items-center justify-center rounded-full text-[13px] font-bold leading-none text-white transition-transform duration-200 group-hover/add:rotate-90"
            style={{ background: accentColor }}
          >
            +
          </span>
          Add a card
        </button>
      )}
    </div>
  );
};
