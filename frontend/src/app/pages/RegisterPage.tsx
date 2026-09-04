import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ApiError } from '@/lib/api/client'
import { useRegister } from '@/lib/api/auth'

export function RegisterPage() {
  const navigate = useNavigate()
  const registerMutation = useRegister()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    try {
      await registerMutation.mutateAsync({ username, password })
      navigate('/')
    } catch {
      // el error se muestra abajo vía registerMutation.isError
    }
  }

  const errorMessage =
    registerMutation.error instanceof ApiError && registerMutation.error.status === 409
      ? 'Ese usuario ya existe.'
      : 'No se pudo crear la cuenta. Revisá los datos e intentá de nuevo.'

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="space-y-1 text-center">
          <h1 className="text-2xl font-semibold">Bolsillito</h1>
          <p className="text-muted-foreground text-sm">Creá tu cuenta</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="register-username">Usuario</Label>
            <Input
              id="register-username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              minLength={3}
              required
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="register-password">Contraseña</Label>
            <Input
              id="register-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
            <p className="text-muted-foreground text-xs">Mínimo 8 caracteres.</p>
          </div>

          {registerMutation.isError && <p className="text-destructive text-sm">{errorMessage}</p>}

          <Button type="submit" className="w-full" disabled={registerMutation.isPending}>
            {registerMutation.isPending ? 'Creando cuenta…' : 'Crear cuenta'}
          </Button>
        </form>

        <p className="text-muted-foreground text-center text-sm">
          ¿Ya tenés cuenta?{' '}
          <Link to="/login" className="text-foreground underline underline-offset-4">
            Ingresá
          </Link>
        </p>
      </div>
    </div>
  )
}
