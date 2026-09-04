import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useThemeStore } from './themeStore'

function mockMatchMedia(matches: boolean) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    })),
  )
}

describe('themeStore', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    useThemeStore.setState({ theme: 'system' })
    document.documentElement.classList.remove('dark')
  })

  it('applies the dark class when theme is set to dark', () => {
    mockMatchMedia(false)
    useThemeStore.getState().setTheme('dark')

    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(useThemeStore.getState().theme).toBe('dark')
  })

  it('removes the dark class when theme is set to light', () => {
    mockMatchMedia(true) // el SO prefiere oscuro, pero "light" explícito gana
    useThemeStore.getState().setTheme('light')

    expect(document.documentElement.classList.contains('dark')).toBe(false)
  })

  it('follows the OS preference when theme is system', () => {
    mockMatchMedia(true)
    useThemeStore.getState().setTheme('system')

    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})
