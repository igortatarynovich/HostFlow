import EntityListShellDemo from '../../components/surfaces/EntityListShellDemo'

/** DEV-only public smoke route: `/dev/entity-list-shell` (no auth). */
export default function EntityListShellDemoPublicPage() {
  return (
    <div className="app-ui min-h-screen bg-slate-50">
      <EntityListShellDemo />
    </div>
  )
}
