import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useLogin } from '@/lib/api/auth'

export function LoginPage() {
  const navigate = useNavigate()
  const login = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await login.mutateAsync({ username, password })
      navigate('/')
    } catch {
      // el error se muestra abajo vía login.isError
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">Bolsillito</h1>
          <p className="text-muted-foreground text-sm">Iniciá sesión para continuar</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="login-username">Usuario</Label>
            <Input
              id="login-username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="login-password">Contraseña</Label>
            <Input
              id="login-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {login.isError && (
            <p className="text-destructive text-sm">Usuario o contraseña incorrectos.</p>
          )}

          <Button type="submit" className="w-full" disabled={login.isPending}>
            {login.isPending ? 'Ingresando…' : 'Ingresar'}
          </Button>
        </form>

        <p className="text-muted-foreground text-center text-sm">
          ¿No tenés cuenta?{' '}
          <Link to="/registro" className="text-foreground underline underline-offset-4">
            Registrate
          </Link>
        </p>
      </div>
    </div>
  )
}
