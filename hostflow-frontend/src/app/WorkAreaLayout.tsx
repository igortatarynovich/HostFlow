import { Outlet } from 'react-router-dom'

/**
 * Shell for **`/app/work`** (SSOT §2.13): index = hub; future child routes render here without changing canonical Work URLs elsewhere.
 */
export function WorkAreaLayout() {
  return <Outlet />
}
