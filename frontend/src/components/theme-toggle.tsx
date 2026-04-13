import { MoonStar, SunMedium } from "lucide-react"

import { Switch } from "@/components/ui/switch"

interface ThemeToggleProps {
  checked: boolean
  onCheckedChange: (checked: boolean) => void
}

export function ThemeToggle({ checked, onCheckedChange }: ThemeToggleProps) {
  return (
    <div className="flex items-center gap-2 rounded-md border px-3 py-2">
      {checked ? <MoonStar className="size-4 text-muted-foreground" /> : <SunMedium className="size-4 text-muted-foreground" />}
      <Switch checked={checked} onCheckedChange={onCheckedChange} aria-label="Toggle color theme" />
    </div>
  )
}
