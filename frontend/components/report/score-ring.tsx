import { cn } from "@/lib/utils";

interface ScoreRingProps {
  score: number | null;
  size?: number;
}

// Reused for both the report headline score and per-module sub-scores, per
// FBP §19 "one interaction pattern, reused everywhere."
export function ScoreRing({ score, size = 96 }: ScoreRingProps) {
  const radius = (size - 10) / 2;
  const circumference = 2 * Math.PI * radius;
  const pct = score ?? 0;
  const offset = circumference - (pct / 100) * circumference;

  const colorClass =
    score === null
      ? "stroke-muted-foreground/40"
      : score >= 80
        ? "stroke-success"
        : score >= 60
          ? "stroke-warning"
          : "stroke-destructive";

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={8}
          fill="none"
          className="stroke-secondary"
        />
        {score !== null && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            strokeWidth={8}
            fill="none"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className={cn("transition-all duration-500", colorClass)}
          />
        )}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-xl font-semibold">{score !== null ? score.toFixed(0) : "—"}</span>
        {score !== null && <span className="text-[10px] text-muted-foreground">/ 100</span>}
      </div>
    </div>
  );
}
