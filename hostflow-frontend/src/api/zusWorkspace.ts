import http from './http'

export type ZusWorkspaceLane =
  | 'task_queue'
  | 'form_status'
  | 'checklist_register'
  | 'checklist_deregister'
  | 'monthly_settlement'
  | 'export_queue'

export type ZusWorkspaceTask = {
  id: string
  tenant_id: string
  employee_id: string
  employee_display_name: string
  workspace_lane: string
  task_kind: string
  form_kind?: string | null
  form_status?: string | null
  status: string
  due_at?: string | null
  assigned_hr_user_id?: string | null
  export_status?: string | null
  checklist_json?: unknown
  title: string
  notes?: string | null
  created_at: string
  updated_at: string
}

export type ZusWorkspaceTaskPage = {
  items: ZusWorkspaceTask[]
  total: number
}

export type ZusWorkspaceTaskListParams = {
  status?: string
  workspace_lane?: string
  task_kind?: string
  form_kind?: string
  due_before?: string
  due_after?: string
  assigned_hr_user_id?: string
  limit?: number
  offset?: number
}

export async function listZusWorkspaceTasks(params?: ZusWorkspaceTaskListParams): Promise<ZusWorkspaceTaskPage> {
  const { data } = await http.get<ZusWorkspaceTaskPage>('/workforce/zus-workspace/tasks', {
    params: {
      status: params?.status || undefined,
      workspace_lane: params?.workspace_lane || undefined,
      task_kind: params?.task_kind?.trim() || undefined,
      form_kind: params?.form_kind || undefined,
      due_before: params?.due_before || undefined,
      due_after: params?.due_after || undefined,
      assigned_hr_user_id: params?.assigned_hr_user_id?.trim() || undefined,
      limit: params?.limit,
      offset: params?.offset,
    },
  })
  return data
}

export async function createZusWorkspaceTask(payload: {
  employee_id: string
  workspace_lane: string
  task_kind: string
  title?: string
  form_kind?: string | null
  form_status?: string | null
  status?: string
  due_at?: string | null
  assigned_hr_user_id?: string | null
  export_status?: string | null
  checklist_json?: unknown
  notes?: string | null
}): Promise<ZusWorkspaceTask> {
  const { data } = await http.post<ZusWorkspaceTask>('/workforce/zus-workspace/tasks', payload)
  return data
}

export async function patchZusWorkspaceTask(
  taskId: string,
  payload: Partial<
    Pick<
      ZusWorkspaceTask,
      | 'workspace_lane'
      | 'task_kind'
      | 'title'
      | 'form_kind'
      | 'form_status'
      | 'status'
      | 'due_at'
      | 'assigned_hr_user_id'
      | 'export_status'
      | 'notes'
    >
  > & { checklist_json?: unknown },
): Promise<ZusWorkspaceTask> {
  const { data } = await http.patch<ZusWorkspaceTask>(
    `/workforce/zus-workspace/tasks/${encodeURIComponent(taskId)}`,
    payload,
  )
  return data
}
