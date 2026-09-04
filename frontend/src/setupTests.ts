import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import '@testing-library/jest-dom/vitest'

afterEach(() => {
  cleanup()
})

// jsdom no implementa estas APIs; Radix UI (usado por shadcn Select/Dialog) las necesita para
// manejar eventos de puntero. Sin este polyfill, los tests que interactúan con esos componentes
// fallan con errores no relacionados a la lógica que se está probando.
if (!Element.prototype.hasPointerCapture) {
  Element.prototype.hasPointerCapture = () => false
}
if (!Element.prototype.releasePointerCapture) {
  Element.prototype.releasePointerCapture = () => {}
}
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}
