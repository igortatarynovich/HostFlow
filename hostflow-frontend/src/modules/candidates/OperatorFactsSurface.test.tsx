import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { OperatorFactsForm, type OperatorFactsView } from './OperatorFactsSurface'

function view(partial: Partial<OperatorFactsView> & Pick<OperatorFactsView, 'steps'>): OperatorFactsView {
  return {
    upload_codes: [],
    asks_file: false,
    ce_code95: { progress: 'needs_input', evidence_shape: null, upload_codes: [], asks_file: false },
    ...partial,
  }
}

describe('OperatorFactsForm', () => {
  it('hides stay and work for a Polish candidate', () => {
    render(
      <OperatorFactsForm
        onPatch={() => undefined}
        view={view({
          citizenship_class: 'pl',
          steps: [
            { key: 'citizenship', visible: true, stored: 'PL' },
            { key: 'stay_basis', visible: false },
            { key: 'work', visible: false },
            { key: 'driving_licence', visible: true, issuing_country: null, categories: [] },
            { key: 'code95', visible: true, presence: null },
            { key: 'tachograph', visible: true, presence: null },
            { key: 'adr', visible: true, presence: null },
          ],
        })}
      />,
    )
    expect(screen.getByTestId('operator-facts-driver')).toBeTruthy()
    expect(screen.getByTestId('operator-facts-work-rights')).toBeTruthy()
    expect(screen.getByTestId('operator-facts-citizenship')).toBeTruthy()
    expect(screen.queryByTestId('operator-facts-stay')).toBeNull()
    expect(screen.queryByTestId('operator-facts-work')).toBeNull()
    expect(screen.getByTestId('operator-facts-uploads-empty')).toBeTruthy()
  })

  it('opens stay for a third-country candidate and does not ask for a file', () => {
    render(
      <OperatorFactsForm
        onPatch={() => undefined}
        view={view({
          citizenship_class: 'third_country',
          steps: [
            { key: 'citizenship', visible: true, stored: 'BY' },
            { key: 'stay_basis', visible: true, stored: null },
            { key: 'work', visible: false },
            { key: 'driving_licence', visible: true, issuing_country: null, categories: [] },
            { key: 'code95', visible: true, presence: null, asks_file: false },
            { key: 'tachograph', visible: true, presence: null, asks_file: false },
            { key: 'adr', visible: true, presence: null, asks_file: false },
          ],
        })}
      />,
    )
    expect(screen.getByTestId('operator-facts-stay')).toBeTruthy()
    expect(screen.queryByTestId('operator-facts-work')).toBeNull()
    expect(screen.getByTestId('operator-facts-evidence').textContent).toMatch(/No file/i)
  })

  it('shows the work permit label for separate_required and work_permit_a', () => {
    render(
      <OperatorFactsForm
        onPatch={() => undefined}
        view={view({
          steps: [
            { key: 'citizenship', visible: true, stored: 'BY' },
            { key: 'stay_basis', visible: true, stored: 'karta_pobytu' },
            {
              key: 'work',
              visible: true,
              work_authorization_basis: 'separate_required',
              procedure_type: 'work_permit_a',
            },
            { key: 'valid_for_this_employment', visible: true, stored: 'operator_verification' },
            { key: 'driving_licence', visible: true, issuing_country: null, categories: [] },
            { key: 'code95', visible: true, presence: null },
            { key: 'tachograph', visible: true, presence: null },
            { key: 'adr', visible: true, presence: null },
          ],
        })}
      />,
    )
    expect((screen.getByTestId('operator-facts-work-input') as HTMLSelectElement).value).toBe('work_permit')
    expect(screen.getByTestId('operator-facts-procedure').textContent).toMatch(/work_permit_a/)
    expect(screen.getByTestId('operator-facts-legal-status').textContent).toMatch(/operator_verification/)
  })

  it('asks for shared evidence only after the issuing country is known', () => {
    const { rerender } = render(
      <OperatorFactsForm
        onPatch={() => undefined}
        view={view({
          steps: [
            { key: 'citizenship', visible: true, stored: 'PL' },
            { key: 'stay_basis', visible: false },
            { key: 'work', visible: false },
            { key: 'driving_licence', visible: true, issuing_country: null, categories: [] },
            { key: 'code95', visible: true, presence: null, evidence_shape: null, asks_file: false },
            { key: 'tachograph', visible: true, presence: null },
            { key: 'adr', visible: true, presence: null },
          ],
          upload_codes: [],
          ce_code95: { evidence_shape: null, upload_codes: [], asks_file: false, progress: 'needs_input' },
        })}
      />,
    )
    expect(screen.queryByTestId('operator-facts-uploads')).toBeNull()

    rerender(
      <OperatorFactsForm
        onPatch={() => undefined}
        view={view({
          steps: [
            { key: 'citizenship', visible: true, stored: 'PL' },
            { key: 'stay_basis', visible: false },
            { key: 'work', visible: false },
            { key: 'driving_licence', visible: true, issuing_country: 'PL', categories: ['CE'] },
            { key: 'code95', visible: true, presence: null, evidence_shape: 'shared', asks_file: true },
            { key: 'tachograph', visible: true, presence: null },
            { key: 'adr', visible: true, presence: null },
          ],
          upload_codes: ['driver_license_code95'],
          ce_code95: {
            evidence_shape: 'shared',
            evidence_variant: 'combined_eu_license',
            upload_codes: ['driver_license_code95'],
            asks_file: true,
          },
        })}
      />,
    )
    expect(screen.getByTestId('operator-facts-evidence').textContent).toMatch(/Shared evidence/i)
    expect(screen.getByTestId('operator-facts-uploads').textContent).toBe('driver_license_code95')
  })
})
