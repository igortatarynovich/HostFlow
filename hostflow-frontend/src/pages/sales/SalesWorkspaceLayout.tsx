import { Outlet } from 'react-router-dom'

export default function SalesWorkspaceLayout() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
