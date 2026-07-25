import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DynamicField } from "@/components/collection/dynamic-field";
import type { FieldDefinition, FieldValue } from "@/lib/types";

export function SectionCard({
  section,
  fields,
  values,
  fieldStates,
  onChange,
  onVerifiedChange,
}: {
  section: string;
  fields: FieldDefinition[];
  values: Record<string, unknown>;
  fieldStates: Record<string, FieldValue>;
  onChange: (key: string, value: unknown) => void;
  onVerifiedChange: (key: string, verified: boolean) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{section}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-5 sm:grid-cols-2">
        {fields.map((definition) => (
          <DynamicField
            key={definition.key}
            definition={definition}
            fieldValue={fieldStates[definition.key]}
            rawValue={values[definition.key]}
            onChange={onChange}
            onVerifiedChange={onVerifiedChange}
          />
        ))}
      </CardContent>
    </Card>
  );
}
