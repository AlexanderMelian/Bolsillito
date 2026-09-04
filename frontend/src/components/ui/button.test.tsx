import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { Button } from '@/components/ui/button'

describe('Button', () => {
  it('renders its children', () => {
    render(<Button>Guardar</Button>)
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Guardar</Button>)

    await userEvent.click(screen.getByRole('button', { name: 'Guardar' }))

    expect(onClick).toHaveBeenCalledOnce()
  })

  it('is disabled when the disabled prop is set', () => {
    render(<Button disabled>Guardar</Button>)
    expect(screen.getByRole('button', { name: 'Guardar' })).toBeDisabled()
  })
})
