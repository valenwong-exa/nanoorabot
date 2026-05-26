import { useState } from "react";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { Eye, EyeOff } from "lucide-react";
import { cn, isMasked } from "../../lib/utils";

interface SecretInputProps {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

export function SecretInput({
  value,
  onChange,
  placeholder,
  className,
}: SecretInputProps) {
  const [visible, setVisible] = useState(false);
  const masked = isMasked(value);

  return (
    <div className={cn("relative flex items-center", className)}>
      <Input
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="pr-10 font-mono text-sm"
        onFocus={(e) => {
          if (masked) e.target.select();
        }}
      />
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="absolute right-0 h-full px-3 text-muted-foreground hover:text-foreground"
        onClick={() => setVisible((v) => !v)}
      >
        {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
      </Button>
    </div>
  );
}
