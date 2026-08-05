"use client";

import { AlertTriangle, CheckCircle2, XCircle } from "lucide-react";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SelectNative } from "@/components/ui/select-native";
import { Textarea } from "@/components/ui/textarea";
import { InfoTooltip } from "@/components/ui/tooltip";
import { ClassificationBadge } from "@/components/collection/classification-badge";
import { FRIENDLY_FIELD_TOOLTIPS, friendlyFieldLabel } from "@/lib/friendly-labels";
import { cn } from "@/lib/utils";
import type { ExperienceMode } from "@/lib/field-modes";
import type { FieldDefinition, FieldValue } from "@/lib/types";

interface DynamicFieldProps {
  definition: FieldDefinition;
  fieldValue: FieldValue | undefined;
  rawValue: unknown;
  onChange: (key: string, value: unknown) => void;
  onVerifiedChange: (key: string, verified: boolean) => void;
  mode: ExperienceMode;
}

// One renderer for every field in the registry, driven entirely by its
// FieldDefinition — no per-field bespoke component (FBP §19 consistency
// rule, applied to the Data Collection form). The classification badge
// (Auto Detect / Calculated / etc.) is engineering vocabulary — only
// Enterprise mode's audience wants it; Beginner/Professional just see a
// clean label and input.
export function DynamicField({ definition, fieldValue, rawValue, onChange, onVerifiedChange, mode }: DynamicFieldProps) {
  const isCalculated = definition.collection_type === "calculated";
  const status = fieldValue?.status ?? "missing";
  const label = friendlyFieldLabel(definition.key, definition.label, mode);
  const tooltip = mode !== "enterprise" ? FRIENDLY_FIELD_TOOLTIPS[definition.key] : undefined;

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap items-center justify-between gap-1.5">
        <Label htmlFor={definition.key} className="flex items-center gap-1.5">
          {label}
          {definition.required && <span className="text-destructive">*</span>}
          {definition.unit && <span className="text-xs text-muted-foreground">({definition.unit})</span>}
          {tooltip && <InfoTooltip text={tooltip} />}
        </Label>
        {mode === "enterprise" && (
          <ClassificationBadge classification={fieldValue?.effective_classification ?? "user_input_required"} />
        )}
      </div>

      {isCalculated ? (
        <div className="flex h-9 items-center rounded-md border border-dashed border-border bg-secondary/30 px-3 text-sm text-muted-foreground">
          {rawValue === null || rawValue === undefined || rawValue === "" ? (
            <span>Will be calculated once required inputs are filled</span>
          ) : (
            <span className="font-medium text-foreground">{String(rawValue)}</span>
          )}
        </div>
      ) : definition.data_type === "boolean" ? (
        <label className="flex h-9 items-center gap-2 text-sm">
          <input
            id={definition.key}
            type="checkbox"
            className="h-4 w-4 accent-primary"
            checked={Boolean(rawValue)}
            onChange={(e) => onChange(definition.key, e.target.checked)}
          />
          Yes
        </label>
      ) : definition.data_type === "enum" ? (
        <SelectNative
          id={definition.key}
          value={typeof rawValue === "string" ? rawValue : ""}
          onChange={(e) => onChange(definition.key, e.target.value || undefined)}
        >
          <option value="">Select...</option>
          {definition.enum_options?.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </SelectNative>
      ) : definition.data_type === "long_text" ? (
        <Textarea
          id={definition.key}
          value={typeof rawValue === "string" ? rawValue : ""}
          onChange={(e) => onChange(definition.key, e.target.value)}
        />
      ) : definition.data_type === "number" ? (
        <Input
          id={definition.key}
          type="number"
          step="any"
          className={cn(status === "invalid" && "border-destructive")}
          value={rawValue === null || rawValue === undefined ? "" : String(rawValue)}
          onChange={(e) => onChange(definition.key, e.target.value === "" ? undefined : Number(e.target.value))}
        />
      ) : (
        <Input
          id={definition.key}
          type="text"
          className={cn(status === "invalid" && "border-destructive")}
          value={typeof rawValue === "string" ? rawValue : ""}
          onChange={(e) => onChange(definition.key, e.target.value || undefined)}
        />
      )}

      {definition.help_text && !fieldValue?.errors.length && !fieldValue?.warnings.length && (
        <p className="text-xs text-muted-foreground">{definition.help_text}</p>
      )}

      {fieldValue?.errors.map((err) => (
        <p key={err} className="flex items-center gap-1 text-xs text-destructive">
          <XCircle className="h-3 w-3 shrink-0" />
          {err}
        </p>
      ))}
      {fieldValue?.warnings.map((warn) => (
        <p key={warn} className="flex items-center gap-1 text-xs text-warning">
          <AlertTriangle className="h-3 w-3 shrink-0" />
          {warn}
        </p>
      ))}

      {definition.requires_manual_verification && status === "filled" && (
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <input
            type="checkbox"
            className="h-3.5 w-3.5 accent-primary"
            checked={fieldValue?.verified ?? false}
            onChange={(e) => onVerifiedChange(definition.key, e.target.checked)}
          />
          {fieldValue?.verified ? (
            <span className="flex items-center gap-1 text-success">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {mode === "enterprise" ? "Verified" : "Confirmed"}
            </span>
          ) : mode === "enterprise" ? (
            "Mark as manually verified"
          ) : (
            "I've double-checked this"
          )}
        </label>
      )}
    </div>
  );
}
