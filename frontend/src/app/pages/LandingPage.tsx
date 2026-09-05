import { useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import {
  Banknote,
  CalendarClock,
  CreditCard,
  Landmark,
  LayoutDashboard,
  LineChart,
  Menu,
  Repeat,
  ShieldCheck,
  Sparkles,
  Star,
  Tags,
  Wallet,
  X,
} from 'lucide-react'

// Landing pública de Bolsillito. Vive fuera del layout autenticado (App.tsx la monta
// directo, sin el header/Nav del dashboard) y define su propia paleta oscura: no toca
// los tokens de --background/--foreground que usa el resto de la app.
//
// Bolsillito es una app de seguimiento de finanzas personales (cuentas, tarjetas,
// categorías, inversiones) -- no emite tarjetas ni mueve dinero. La copy de esta página
// describe eso, no beneficios de una billetera/neobank.

const NAV_LINKS = [
  { href: '#beneficios', label: 'Beneficios' },
  { href: '#como-funciona', label: 'Cómo funciona' },
  { href: '#ayuda', label: 'Ayuda' },
]

const FEATURES = [
  {
    title: 'Patrimonio total, siempre a mano',
    description:
      'Sumás cuentas de banco, efectivo y billeteras virtuales, en pesos y en dólares, y ves cuánto tenés realmente hoy.',
    icon: LayoutDashboard,
    span: 'lg:col-span-2 lg:row-span-2',
    highlight: true,
  },
  {
    title: 'Tarjetas y cuotas bajo control',
    description: 'Débito y crédito, con cada cuota y la fecha de cierre del resumen sin sorpresas.',
    icon: CreditCard,
    span: '',
    highlight: false,
  },
  {
    title: 'Categorías que arman el panorama',
    description: 'Cada gasto y cada ingreso categorizado, para saber en qué se te va la plata cada mes.',
    icon: Tags,
    span: '',
    highlight: false,
  },
  {
    title: 'Inversiones en el mismo lugar',
    description: 'Acciones, bonos, cripto y fondos, con precio promedio y ganancia calculados solos.',
    icon: LineChart,
    span: '',
    highlight: false,
  },
  {
    title: 'Tus datos, solo tuyos',
    description: 'Cuenta propia con usuario y contraseña. Nadie más ve tus cuentas ni tus movimientos.',
    icon: ShieldCheck,
    span: '',
    highlight: false,
  },
]

const STEPS = [
  {
    number: '1',
    title: 'Creá tu cuenta',
    description: 'Usuario y contraseña. Cada cuenta ve solo sus propios datos.',
    icon: Wallet,
  },
  {
    number: '2',
    title: 'Cargá tus cuentas y tarjetas',
    description: 'Banco, efectivo, billetera virtual, débito o crédito: las que uses en el día a día.',
    icon: Landmark,
  },
  {
    number: '3',
    title: 'Registrá tus movimientos',
    description: 'Ingresos, gastos y transferencias, categorizados. Bolsillito arma el resto.',
    icon: Repeat,
  },
]

const TESTIMONIALS = [
  {
    name: 'Julieta Marino',
    location: 'Rosario, Santa Fe',
    quote:
      'Antes tenía todo en una planilla que se desactualizaba sola. Ahora entro a Bolsillito y veo mi plata real, al momento.',
  },
  {
    name: 'Nicolás Ferreyra',
    location: 'Córdoba Capital',
    quote:
      'Con las compras en cuotas nunca sabía cuánto me quedaba pendiente. Ahora lo veo resumen por resumen, sin sorpresas.',
  },
  {
    name: 'Camila Suárez',
    location: 'CABA',
    quote:
      'Tengo ahorros en pesos, en dólares y en acciones. Es la primera vez que los veo todos juntos, en un solo lugar.',
  },
]

const ACCOUNT_KINDS = [
  { label: 'Cuentas de banco', icon: Landmark },
  { label: 'Efectivo', icon: Banknote },
  { label: 'Billeteras virtuales', icon: Wallet },
  { label: 'Inversiones', icon: LineChart },
]

function Reveal({ children, delay = 0, className = '' }: { children: ReactNode; delay?: number; className?: string }) {
  return (
    <div
      className={`motion-safe:animate-[landing-rise_0.7s_ease-out_both] ${className}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      {children}
    </div>
  )
}

export function LandingPage() {
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="font-dm min-h-screen bg-[#08090c] text-zinc-100 antialiased selection:bg-emerald-400/30 selection:text-emerald-100">
      <style>{`
        @keyframes landing-rise {
          from { opacity: 0; transform: translateY(14px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      {/* Navbar */}
      <header className="sticky top-0 z-40 border-b border-white/5 bg-[#08090c]/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="font-jakarta text-lg font-bold tracking-tight text-zinc-50">
            Bolsillito
          </Link>

          <nav className="hidden items-center gap-8 md:flex">
            {NAV_LINKS.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="text-sm text-zinc-400 transition-colors hover:text-zinc-100"
              >
                {link.label}
              </a>
            ))}
          </nav>

          <div className="hidden md:block">
            <Link
              to="/login"
              className="rounded-full bg-emerald-400 px-5 py-2.5 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-300"
            >
              Ingresar
            </Link>
          </div>

          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            className="text-zinc-300 md:hidden"
            aria-label={menuOpen ? 'Cerrar menú' : 'Abrir menú'}
            aria-expanded={menuOpen}
          >
            {menuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {menuOpen && (
          <div className="border-t border-white/5 px-6 py-4 md:hidden">
            <nav className="flex flex-col gap-4">
              {NAV_LINKS.map((link) => (
                <a
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="text-sm text-zinc-300"
                >
                  {link.label}
                </a>
              ))}
              <Link
                to="/login"
                className="mt-2 rounded-full bg-emerald-400 px-5 py-2.5 text-center text-sm font-semibold text-zinc-950"
              >
                Ingresar
              </Link>
            </nav>
          </div>
        )}
      </header>

      <main>
        {/* Hero */}
        <section className="relative overflow-hidden">
          <div
            className="pointer-events-none absolute -top-32 left-1/2 h-[36rem] w-[36rem] -translate-x-1/2 rounded-full bg-emerald-500/10 blur-[120px]"
            aria-hidden="true"
          />
          <div className="relative mx-auto grid max-w-6xl gap-16 px-6 pt-16 pb-24 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:pt-24 lg:pb-32">
            <div>
              <Reveal>
                <h1 className="font-jakarta text-4xl leading-[1.08] font-extrabold tracking-tight text-zinc-50 sm:text-5xl lg:text-6xl">
                  Tus finanzas personales, sin planillas
                </h1>
              </Reveal>
              <Reveal delay={90}>
                <p className="mt-6 max-w-md text-lg text-zinc-400">
                  Todas tus cuentas, tarjetas e inversiones en un solo lugar. Sabés cuánto tenés y en
                  qué se te va, sin abrir un Excel.
                </p>
              </Reveal>
              <Reveal delay={180}>
                <div className="mt-9 flex flex-wrap items-center gap-4">
                  <Link
                    to="/registro"
                    className="rounded-full bg-emerald-400 px-7 py-3.5 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-300"
                  >
                    Crear cuenta gratis
                  </Link>
                  <a
                    href="#beneficios"
                    className="rounded-full border border-white/15 px-7 py-3.5 text-sm font-semibold text-zinc-100 transition-colors hover:border-white/30 hover:bg-white/5"
                  >
                    Ver beneficios
                  </a>
                </div>
              </Reveal>
              <Reveal delay={260}>
                <p className="mt-10 text-sm text-zinc-500">
                  Gratis, sin límite de cuentas ni de tarjetas.
                </p>
              </Reveal>
            </div>

            <Reveal delay={200} className="relative mx-auto w-full max-w-sm lg:mx-0">
              {/* Movimientos recientes, detrás */}
              <div className="absolute top-16 right-2 h-[26rem] w-56 rotate-[4deg] rounded-[2.2rem] border border-white/10 bg-[#0d1013] shadow-2xl shadow-black/60 sm:right-6">
                <div className="flex h-full flex-col justify-end gap-3 p-5">
                  <p className="text-xs text-zinc-500">Últimos movimientos</p>
                  <div className="space-y-2 rounded-2xl bg-white/5 p-3">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-400">Sueldo</span>
                      <span className="font-medium text-emerald-400">+$ 350.000</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-400">Alquiler</span>
                      <span className="text-zinc-200">-$ 180.000</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-400">Supermercado</span>
                      <span className="text-zinc-200">-$ 42.300</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Resumen de patrimonio, adelante */}
              <div className="relative -rotate-[7deg] rounded-3xl border border-white/15 bg-gradient-to-br from-white/[0.09] to-white/[0.02] p-6 shadow-2xl shadow-black/70 backdrop-blur-xl">
                <div className="flex items-center justify-between">
                  <LayoutDashboard className="h-6 w-6 text-emerald-300" />
                  <span className="font-jakarta text-sm font-semibold tracking-wide text-zinc-200">
                    Bolsillito
                  </span>
                </div>
                <p className="mt-8 text-xs text-zinc-400">Patrimonio total</p>
                <p className="font-jakarta mt-1 text-3xl font-bold text-zinc-50">$ 1.842.300</p>
                <p className="mt-1 text-xs text-zinc-400">+ US$ 2.480 en dólares</p>

                <div className="mt-6 flex h-2 overflow-hidden rounded-full bg-white/10">
                  <div className="h-full w-[70%] bg-emerald-400" />
                  <div className="h-full w-[30%] bg-amber-300" />
                </div>
                <div className="mt-2 flex justify-between text-[11px] text-zinc-400">
                  <span>Pesos</span>
                  <span>Dólares</span>
                </div>
              </div>
            </Reveal>
          </div>
        </section>

        {/* Para qué cuentas está pensada */}
        <section className="border-y border-white/5 bg-white/[0.02] py-10">
          <div className="mx-auto flex max-w-6xl flex-col items-center gap-6 px-6 sm:flex-row sm:justify-between">
            <p className="text-sm text-zinc-500">Pensada para</p>
            <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
              {ACCOUNT_KINDS.map(({ label, icon: Icon }) => (
                <span key={label} className="flex items-center gap-2 text-sm font-medium text-zinc-400">
                  <Icon className="h-4 w-4 text-zinc-500" />
                  {label}
                </span>
              ))}
            </div>
          </div>
        </section>

        {/* Bento de features */}
        <section id="beneficios" className="mx-auto max-w-6xl px-6 py-24">
          <Reveal className="max-w-xl">
            <h2 className="font-jakarta text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
              Todo lo que hoy llevás en la cabeza, ordenado
            </h2>
            <p className="mt-4 text-zinc-400">
              Bolsillito no mueve tu plata: la registra y te la muestra clara, cuenta por cuenta.
            </p>
          </Reveal>

          <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:grid-rows-2">
            {FEATURES.map((feature, index) => {
              const Icon = feature.icon
              return (
                <Reveal key={feature.title} delay={index * 70} className={feature.span}>
                  <div
                    className={`group h-full rounded-2xl border border-white/10 bg-white/[0.04] p-6 transition-all duration-300 hover:scale-[1.02] hover:border-white/20 ${
                      feature.span ? 'flex flex-col justify-between' : ''
                    }`}
                  >
                    <div className="inline-flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-400/15 text-emerald-300">
                      <Icon className="h-5 w-5" />
                    </div>
                    <div className="mt-5">
                      <h3 className="font-jakarta text-lg font-semibold text-zinc-50">{feature.title}</h3>
                      <p className="mt-2 text-sm leading-relaxed text-zinc-400">{feature.description}</p>
                    </div>
                    {feature.highlight && (
                      <div className="mt-8 flex items-center gap-3 text-sm text-zinc-400">
                        <CalendarClock className="h-4 w-4 text-amber-300" />
                        Con proyección de flujo de caja para los próximos meses.
                      </div>
                    )}
                  </div>
                </Reveal>
              )
            })}
          </div>
        </section>

        {/* Pasos */}
        <section id="como-funciona" className="border-t border-white/5 bg-white/[0.02] py-24">
          <div className="mx-auto max-w-6xl px-6">
            <Reveal className="max-w-xl">
              <h2 className="font-jakarta text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
                Empezar te lleva tres pasos
              </h2>
            </Reveal>

            <div className="relative mt-16 grid grid-cols-1 gap-12 md:grid-cols-3 md:gap-8">
              <div
                className="absolute top-7 right-0 left-0 hidden h-px bg-white/10 md:block"
                aria-hidden="true"
              />
              {STEPS.map((step, index) => {
                const Icon = step.icon
                return (
                  <Reveal key={step.number} delay={index * 100} className="relative">
                    <div className="relative flex h-14 w-14 items-center justify-center rounded-2xl border border-white/15 bg-[#08090c]">
                      <Icon className="h-6 w-6 text-emerald-300" />
                      <span className="font-jakarta absolute -top-3 -right-3 flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400 text-xs font-bold text-zinc-950">
                        {step.number}
                      </span>
                    </div>
                    <h3 className="font-jakarta mt-6 text-xl font-semibold text-zinc-50">{step.title}</h3>
                    <p className="mt-2 max-w-xs text-sm leading-relaxed text-zinc-400">{step.description}</p>
                  </Reveal>
                )
              })}
            </div>
          </div>
        </section>

        {/* Testimonios */}
        <section className="mx-auto max-w-6xl px-6 py-24">
          <Reveal className="max-w-xl">
            <h2 className="font-jakarta text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
              Gente que ya ordenó su plata
            </h2>
          </Reveal>

          <div className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-3">
            {TESTIMONIALS.map((testimonial, index) => (
              <Reveal key={testimonial.name} delay={index * 90}>
                <div className="h-full rounded-2xl border border-white/10 bg-white/[0.04] p-6">
                  <div className="flex gap-0.5 text-emerald-300">
                    {Array.from({ length: 5 }).map((_, starIndex) => (
                      <Star key={starIndex} className="h-4 w-4 fill-current" />
                    ))}
                  </div>
                  <p className="mt-4 text-sm leading-relaxed text-zinc-300">“{testimonial.quote}”</p>
                  <div className="mt-6">
                    <p className="text-sm font-semibold text-zinc-100">{testimonial.name}</p>
                    <p className="text-xs text-zinc-500">{testimonial.location}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </section>

        {/* CTA final */}
        <section id="ayuda" className="mx-auto max-w-6xl px-6 pb-24">
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-gradient-to-br from-emerald-400/10 via-white/[0.03] to-transparent px-8 py-14 text-center sm:px-16">
              <Sparkles className="mx-auto h-8 w-8 text-emerald-300" />
              <h2 className="font-jakarta mt-5 text-3xl font-bold tracking-tight text-zinc-50 sm:text-4xl">
                Tu plata, ordenada
              </h2>
              <p className="mx-auto mt-4 max-w-md text-zinc-400">
                Creá tu cuenta y armá tu primer mes en cinco minutos.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
                <Link
                  to="/registro"
                  className="rounded-full bg-emerald-400 px-7 py-3.5 text-sm font-semibold text-zinc-950 transition-colors hover:bg-emerald-300"
                >
                  Crear mi cuenta
                </Link>
                <Link
                  to="/login"
                  className="text-sm font-medium text-zinc-300 underline underline-offset-4 hover:text-zinc-100"
                >
                  Ya tengo cuenta
                </Link>
              </div>
            </div>
          </Reveal>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5">
        <div className="mx-auto max-w-6xl px-6 py-14">
          <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
            <div className="col-span-2 sm:col-span-1">
              <p className="font-jakarta text-lg font-bold text-zinc-50">Bolsillito</p>
              <p className="mt-3 text-xs text-zinc-500">Tus finanzas personales, sin planillas</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-zinc-200">Producto</p>
              <ul className="mt-3 space-y-2 text-sm text-zinc-500">
                <li><a href="#beneficios" className="hover:text-zinc-200">Beneficios</a></li>
                <li><a href="#como-funciona" className="hover:text-zinc-200">Cómo funciona</a></li>
                <li><Link to="/registro" className="hover:text-zinc-200">Crear cuenta</Link></li>
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold text-zinc-200">Ayuda</p>
              <ul className="mt-3 space-y-2 text-sm text-zinc-500">
                <li><a href="#ayuda" className="hover:text-zinc-200">Centro de ayuda</a></li>
                <li><a href="#ayuda" className="hover:text-zinc-200">Hablar con nosotros</a></li>
              </ul>
            </div>
            <div>
              <p className="text-sm font-semibold text-zinc-200">Legal</p>
              <ul className="mt-3 space-y-2 text-sm text-zinc-500">
                <li><a href="#" className="hover:text-zinc-200">Términos y condiciones</a></li>
                <li><a href="#" className="hover:text-zinc-200">Privacidad</a></li>
              </ul>
            </div>
          </div>

          <div className="mt-12 flex flex-col-reverse items-center justify-between gap-4 border-t border-white/5 pt-6 sm:flex-row">
            <p className="text-xs text-zinc-600">© 2026 Bolsillito. Todos los derechos reservados.</p>
            <div className="flex gap-4 text-xs text-zinc-500">
              <a href="#" className="hover:text-zinc-200">Instagram</a>
              <a href="#" className="hover:text-zinc-200">LinkedIn</a>
              <a href="#" className="hover:text-zinc-200">X</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
