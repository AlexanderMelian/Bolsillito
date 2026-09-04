import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

import '@testing-library/jest-dom/vitest'

afterEach(() => {
  cleanup()
})

// Node 22+ trae su propio `localStorage` global (activo sin el flag --localstorage-file, que
// deja `setItem`/`clear` rotos) y pisa el de jsdom. stores/themeStore.ts persiste con
// zustand/middleware `persist`, que usa el `localStorage` global -- sin este mock en memoria,
// cualquier test que toque el store rompe con "storage.setItem is not a function".
class MemoryStorage implements Storage {
  private store = new Map<string, string>()
  get length() {
    return this.store.size
  }
  clear() {
    this.store.clear()
  }
  getItem(key: string) {
    return this.store.has(key) ? this.store.get(key)! : null
  }
  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null
  }
  removeItem(key: string) {
    this.store.delete(key)
  }
  setItem(key: string, value: string) {
    this.store.set(key, String(value))
  }
}
Object.defineProperty(globalThis, 'localStorage', {
  value: new MemoryStorage(),
  writable: true,
  configurable: true,
})

afterEach(() => {
  localStorage.clear()
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

// jsdom tampoco implementa matchMedia. stores/themeStore.ts lo llama en el nivel de módulo
// (para escuchar cambios de preferencia del SO), así que sin esto cualquier test que importe
// App o ThemeToggle rompe al cargar el módulo, no al ejercitar el tema. Los tests que sí
// prueban el tema pisan este mock con su propio `vi.stubGlobal('matchMedia', ...)`.
if (!window.matchMedia) {
  window.matchMedia = (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })
}
