import * as React from "react";

import { cn } from "@/lib/utils";

// A native <select>, shadcn-styled — simpler and more robust than a Radix
// combobox for a dynamically-generated form with ~15 enum/boolean fields.
const SelectNative = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(
  ({ className, children, ...props }, ref) => (
    <select
      ref={ref}
      className={cn(
        "flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  ),
);
SelectNative.displayName = "SelectNative";

export { SelectNative };
