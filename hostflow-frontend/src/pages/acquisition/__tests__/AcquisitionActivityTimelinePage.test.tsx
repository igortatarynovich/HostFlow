import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { I18nProvider } from '../../../i18n'
import AcquisitionActivityTimelinePage from '../AcquisitionActivityTimelinePage'
import type { AcquisitionActivityEvent } from '../../../api/acquisitionActivity'

const { mockList } = vi.hoisted(() => ({
  mockList: vi.fn(),
}))

vi.mock('../../../api/acquisitionActivity', () => ({
  listAcquisitionActivity: mockList,
}))

vi.mock('../../../components/nav/PageHeader', () => ({
  PageHeader: ({ title }: { title?: string }) => (title ? <h1>{title}</h1> : null),
}))

function event(id: string, eventType = 'FlightCreated'): AcquisitionActivityEvent {
  return {
    id,
    tenant_id: 't1',
    campaign_id: 'camp-1',
    event_type: eventType,
    event_version: 'v1',
    occurred_at: '2026-07-21T12:00:00Z',
    recorded_at: '2026-07-21T12:00:01Z',
    actor_type: 'system',
    payload: { html: '<b>x</b>' },
  }
}

function renderPage(entry = '/app/acquisition/activity') {
  return render(
    <MemoryRouter initialEntries={[entry]}>
      <I18nProvider>
        <AcquisitionActivityTimelinePage />
      </I18nProvider>
    </MemoryRouter>,
  )
}

describe('AcquisitionActivityTimelinePage', () => {
  beforeEach(() => {
    mockList.mockReset()
  })

  it('shows empty state without campaign_id and does not call API', async () => {
    renderPage()
    expect(await screen.findByTestId('acquisition-activity-empty-campaign')).toBeInTheDocument()
    expect(mockList).not.toHaveBeenCalled()
  })

  it('loads events for campaign_id and shows loading then rows', async () => {
    let resolveList: (value: unknown) => void = () => undefined
    mockList.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveList = resolve
        }),
    )

    renderPage('/app/acquisition/activity?campaign_id=camp-1')
    expect(await screen.findByTestId('acquisition-activity-loading')).toBeInTheDocument()

    resolveList({
      items: [event('e1'), event('e2', 'FlightStarted')],
      next_cursor: { occurred_at: '2026-07-21T12:00:00Z', id: 'e2' },
      order: ['occurred_at', 'id'],
    })

    expect(await screen.findByTestId('acquisition-activity-row-e1')).toBeInTheDocument()
    expect(screen.getByText('Flight Created')).toBeInTheDocument()
    expect(screen.getByText('Flight Started')).toBeInTheDocument()
    expect(mockList).toHaveBeenCalledWith(
      expect.objectContaining({ campaign_id: 'camp-1', limit: 50 }),
    )
  })

  it('shows API error banner', async () => {
    mockList.mockRejectedValue({ response: { status: 500, data: { detail: 'boom' } } })
    renderPage('/app/acquisition/activity?campaign_id=camp-1')
    await waitFor(() => {
      expect(screen.getByText(/Failed to load activity timeline|boom/i)).toBeInTheDocument()
    })
  })

  it('Load more appends without duplicating ids', async () => {
    mockList
      .mockResolvedValueOnce({
        items: [event('e1'), event('e2')],
        next_cursor: { occurred_at: '2026-07-21T12:00:00Z', id: 'e2' },
        order: ['occurred_at', 'id'],
      })
      .mockResolvedValueOnce({
        items: [event('e2'), event('e3')],
        next_cursor: null,
        order: ['occurred_at', 'id'],
      })

    renderPage('/app/acquisition/activity?campaign_id=camp-1')
    await screen.findByTestId('acquisition-activity-row-e1')
    fireEvent.click(screen.getByTestId('acquisition-activity-load-more'))

    await waitFor(() => {
      expect(screen.getByTestId('acquisition-activity-row-e3')).toBeInTheDocument()
    })
    expect(screen.getAllByTestId(/acquisition-activity-row-/)).toHaveLength(3)
    expect(mockList).toHaveBeenLastCalledWith(
      expect.objectContaining({
        after_occurred_at: '2026-07-21T12:00:00Z',
        after_id: 'e2',
      }),
    )
  })

  it('Apply resets list/cursor and reloads without after_*', async () => {
    mockList
      .mockResolvedValueOnce({
        items: [event('e1')],
        next_cursor: { occurred_at: '2026-07-21T12:00:00Z', id: 'e1' },
        order: ['occurred_at', 'id'],
      })
      .mockResolvedValueOnce({
        items: [event('e9', 'EndpointChanged')],
        next_cursor: null,
        order: ['occurred_at', 'id'],
      })

    renderPage('/app/acquisition/activity?campaign_id=camp-1')
    await screen.findByTestId('acquisition-activity-row-e1')

    const campaignInput = screen.getByTestId('acquisition-activity-campaign-id')
    fireEvent.change(campaignInput, { target: { value: 'camp-2' } })
    fireEvent.click(screen.getByRole('button', { name: /Apply/i }))

    await waitFor(() => {
      expect(screen.getByTestId('acquisition-activity-row-e9')).toBeInTheDocument()
    })
    expect(screen.queryByTestId('acquisition-activity-row-e1')).not.toBeInTheDocument()
    expect(mockList).toHaveBeenLastCalledWith(
      expect.objectContaining({ campaign_id: 'camp-2' }),
    )
    expect(mockList.mock.calls.at(-1)?.[0]).not.toHaveProperty('after_id')
  })

  it('renders payload as text in <pre>, not HTML', async () => {
    mockList.mockResolvedValue({
      items: [event('e1')],
      next_cursor: null,
      order: ['occurred_at', 'id'],
    })
    renderPage('/app/acquisition/activity?campaign_id=camp-1')
    await screen.findByTestId('acquisition-activity-row-e1')
    fireEvent.click(screen.getByText('Details'))
    const pre = await screen.findByTestId('acquisition-activity-payload-e1')
    expect(pre.tagName).toBe('PRE')
    expect(pre.textContent).toContain('<b>x</b>')
    expect(pre.querySelector('b')).toBeNull()
  })

  it('has no runtime action buttons (launch/pause/resume)', async () => {
    mockList.mockResolvedValue({ items: [], next_cursor: null, order: ['occurred_at', 'id'] })
    renderPage('/app/acquisition/activity?campaign_id=camp-1')
    await screen.findByTestId('acquisition-activity-empty')
    expect(screen.queryByRole('button', { name: /launch|pause|resume/i })).toBeNull()
  })
})
