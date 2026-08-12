import { Outlet } from 'react-router-dom'

/** Sales route shell — section nav lives in the app sidebar; history back is in WorkspaceBackBar. */
export default function SalesWorkspaceLayout() {
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 overflow-hidden">
        <Outlet />
      </div>
    </div>
  )
}
