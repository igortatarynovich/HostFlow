import { Outlet } from 'react-router-dom'

/** Shell for `/app/work` nested routes. */
export function WorkAreaLayout() {
  return (
    <div><Outlet /></div>
  )
}
