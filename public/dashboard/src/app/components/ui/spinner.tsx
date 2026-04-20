import { cn } from "./utils";

function Spinner({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        "size-8 rounded-full border-[3px] border-muted/70 border-t-primary shadow-[inset_0_1px_2px_rgba(255,255,255,0.08),0_0_0_1px_rgba(255,255,255,0.04)] animate-spin",
        className,
      )}
      {...props}
    />
  );
}

export { Spinner };
