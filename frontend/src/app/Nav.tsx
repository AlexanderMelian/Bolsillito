import { NavLink } from 'react-router-dom'

const LINKS = [
  { to: '/', label: 'Resumen', end: true },
  { to: '/cuentas', label: 'Cuentas' },
  { to: '/movimientos', label: 'Movimientos' },
  { to: '/gastos-fijos', label: 'Gastos fijos' },
  { to: '/inversiones', label: 'Inversiones' },
]

export function Nav() {
  return (
    <nav className="border-border bg-card/95 fixed inset-x-0 bottom-0 z-10 border-t backdrop-blur sm:static sm:border-t-0">
      <ul className="mx-auto flex max-w-3xl justify-around sm:justify-start sm:gap-1 sm:px-6">
        {LINKS.map((link) => (
          <li key={link.to} className="flex-1 sm:flex-none">
            <NavLink
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `block px-3 py-3 text-center text-sm font-medium sm:rounded-lg sm:py-2 ${
                  isActive
                    ? 'text-primary sm:bg-primary/10'
                    : 'text-muted-foreground hover:text-foreground'
                }`
              }
            >
              {link.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
