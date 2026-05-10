import { MinimalAgentShell } from "@/components/layout/minimal-agent-shell";
import { TooltipProvider } from "@/components/ui/tooltip";

export function App() {
  return (
    <TooltipProvider>
      <MinimalAgentShell />
    </TooltipProvider>
  );
}
