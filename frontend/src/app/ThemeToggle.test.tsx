import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { useThemeStore } from '@/stores/themeStore'

import { ThemeToggle } from './ThemeToggle'

describe('ThemeToggle', () => {
  beforeEach(() => {
    useThemeStore.setState({ theme: 'system' })
  })

  afterEach(() => {
    useThemeStore.setState({ theme: 'system' })
    document.documentElement.classList.remove('dark')
  })

  it('cycles light -> dark -> system -> light on each click', async () => {
    render(<ThemeToggle />)
    const button = screen.getByRole('button')
    expect(button).toHaveAccessibleName(/Sistema/)

    await userEvent.click(button)
    expect(useThemeStore.getState().theme).toBe('light')
    expect(button).toHaveAccessibleName(/Claro/)

    await userEvent.click(button)
    expect(useThemeStore.getState().theme).toBe('dark')
    expect(button).toHaveAccessibleName(/Oscuro/)

    await userEvent.click(button)
    expect(useThemeStore.getState().theme).toBe('system')
  })

  it('applies the dark class to the document when cycling into dark', async () => {
    useThemeStore.setState({ theme: 'light' })
    render(<ThemeToggle />)

    await userEvent.click(screen.getByRole('button'))

    expect(document.documentElement.classList.contains('dark')).toBe(true)
  })
})
