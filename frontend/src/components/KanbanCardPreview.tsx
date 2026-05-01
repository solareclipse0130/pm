import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article
    className="rotate-[1deg] rounded-2xl border border-[var(--stroke-strong)] bg-white/95 px-4 py-4 shadow-[0_24px_48px_rgba(15,42,71,0.22)] backdrop-blur"
  >
    <div className="flex items-start justify-between gap-3">
      <div>
        <h4 className="font-display text-base font-semibold leading-snug text-[var(--deep-sea)]">
          {card.title}
        </h4>
        <p className="mt-2 text-sm leading-6 text-[var(--slate)]">
          {card.details}
        </p>
      </div>
    </div>
  </article>
);
