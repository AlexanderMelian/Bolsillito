import { Monitor, Moon, Sun } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { useThemeStore, type Theme } from '@/stores/themeStore'

const ORDER: Theme[] = ['light', 'dark', 'system']
const ICONS: Record<Theme, typeof Sun> = { light: Sun, dark: Moon, system: Monitor }
const LABELS: Record<Theme, string> = { light: 'Claro', dark: 'Oscuro', system: 'Sistema' }

export function ThemeToggle() {
  const theme = useThemeStore((state) => state.theme)
  const setTheme = useThemeStore((state) => state.setTheme)
  const Icon = ICONS[theme]

  const cycleTheme = () => {
    const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length]
    setTheme(next)
  }

  return (
    <Button
      variant="ghost"
      size="icon-sm"
      onClick={cycleTheme}
      aria-label={`Tema: ${LABELS[theme]}. Cambiar tema`}
    >
      <Icon className="size-4" />
    </Button>
  )
}
