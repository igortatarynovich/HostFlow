import { ACTIVATION_PATHS } from '../app/activationRoutes'

/** Browser-only preference: first screen after `/app` or app root (UOS). */
export const DEFAULT_APP_HOME_STORAGE_KEY = 'hf:default_app_home'

/** One-time: users who never set a preference get Tasks as default (when permitted). */
const DEFAULT_APP_HOME_LEGACY_MIGRATION_KEY = 'hf:default_app_home:legacy_v1_tasks'

export type StoredDefaultAppHome = 'overview' | 'tasks'

export function readStoredDefaultAppHome(): StoredDefaultAppHome {
  try {
    const v = window.localStorage.getItem(DEFAULT_APP_HOME_STORAGE_KEY)?.trim().toLowerCase()
    if (v === 'tasks') return 'tasks'
  } catch {
    /* ignore */
  }
  return 'overview'
}

export function writeStoredDefaultAppHome(value: StoredDefaultAppHome): void {
  try {
    window.localStorage.setItem(DEFAULT_APP_HOME_STORAGE_KEY, value)
  } catch {
    /* ignore */
  }
}

export function resolveDefaultAppHomeHref(
  canOpenTasks: boolean,
): typeof ACTIVATION_PATHS.overview | typeof ACTIVATION_PATHS.reminders {
  if (readStoredDefaultAppHome() === 'tasks' && canOpenTasks) return ACTIVATION_PATHS.reminders
  return ACTIVATION_PATHS.overview
}

export function resolveDefaultAppHomeSegment(canOpenTasks: boolean): 'overview' | 'work/tasks' {
  if (readStoredDefaultAppHome() === 'tasks' && canOpenTasks) return 'work/tasks'
  return 'overview'
}

/**
 * First visit after rollout: if `hf:default_app_home` was never set and the user may open Tasks,
 * default to Tasks (matches SSOT “post-login = Tasks” for new/legacy-unset profiles).
 */
export function maybeMigrateDefaultAppHomeToTasks(canOpenTasks: boolean): void {
  if (typeof window === 'undefined') return
  try {
    if (window.localStorage.getItem(DEFAULT_APP_HOME_LEGACY_MIGRATION_KEY) === '1') return
    if (canOpenTasks) {
      const raw = window.localStorage.getItem(DEFAULT_APP_HOME_STORAGE_KEY)
      if (raw == null || String(raw).trim() === '') {
        writeStoredDefaultAppHome('tasks')
      }
    }
    window.localStorage.setItem(DEFAULT_APP_HOME_LEGACY_MIGRATION_KEY, '1')
  } catch {
    /* ignore */
  }
}
