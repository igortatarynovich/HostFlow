import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
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
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
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
    expect(screen.getByTestId('operator-facts-work-determined').textContent).toMatch(/nie są wymagane/i)
    expect(screen.getByTestId('operator-facts-citizenship')).toBeTruthy()
    expect(screen.queryByTestId('operator-facts-stay')).toBeNull()
    expect(screen.queryByTestId('operator-facts-work')).toBeNull()
    expect(screen.queryByTestId('operator-facts-licence-details')).toBeNull()
    expect(screen.queryByText(/Legal Eligibility/i)).toBeNull()
  })

  it('opens stay for a third-country candidate and does not ask for a file', () => {
    render(
      <OperatorFactsForm
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
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
    expect(screen.getByTestId('operator-facts-stay').textContent).toMatch(/Na jakiej podstawie przebywa w Polsce/)
    expect(screen.getByTestId('operator-facts-stay').textContent).toMatch(/Karta pobytu/)
    expect(screen.queryByTestId('operator-facts-work')).toBeNull()
    expect(screen.queryByTestId('operator-facts-card-parameters')).toBeNull()
    expect(screen.queryByText(/Stay basis/i)).toBeNull()
  })

  it('treats visa C or D as the type and does not ask for a purpose', () => {
    render(
      <OperatorFactsForm
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
        onPatch={() => undefined}
        view={view({
          citizenship_class: 'third_country',
          steps: [
            { key: 'citizenship', visible: true, stored: 'BY' },
            { key: 'stay_basis', visible: true, stored: 'visa_d', valid_to: null },
            { key: 'work', visible: true, operator_label: 'unknown' },
            { key: 'driving_licence', visible: true, issuing_country: null, categories: [] },
            { key: 'code95', visible: true, presence: null },
            { key: 'tachograph', visible: true, presence: null },
            { key: 'adr', visible: true, presence: null },
          ],
        })}
      />,
    )
    expect(screen.getByTestId('operator-facts-stay-parameters').textContent).toMatch(/Ważna do/)
    expect(screen.queryByText(/Typ wizy/)).toBeNull()
    expect(screen.queryByText(/Cel wizy/)).toBeNull()
    expect(screen.getByTestId('operator-facts-work')).toBeTruthy()
  })

  it('keeps a partial card date and saves only a complete one', () => {
    const onPatch = vi.fn()
    render(
      <OperatorFactsForm
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
        onPatch={onPatch}
        view={view({
          steps: [
            { key: 'citizenship', visible: true, stored: 'BY' },
            { key: 'stay_basis', visible: true, stored: 'karta_pobytu', valid_to: null },
            { key: 'work', visible: true, operator_label: 'unknown' },
            { key: 'driving_licence', visible: true, issuing_country: null, categories: [] },
            { key: 'code95', visible: true, presence: null },
            { key: 'tachograph', visible: true, presence: null },
            { key: 'adr', visible: true, presence: null },
          ],
        })}
      />,
    )
    const input = screen.getByTestId('operator-facts-stay-valid-to') as HTMLInputElement
    fireEvent.change(input, { target: { value: '' } })
    expect(onPatch).not.toHaveBeenCalled()
    fireEvent.change(input, { target: { value: '2027-01-15' } })
    expect(onPatch).toHaveBeenCalledWith({ stay_valid_to: '2027-01-15' })
  })

  it('shows the work permit label for separate_required and work_permit_a', () => {
    render(
      <OperatorFactsForm
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
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
    expect(screen.getByTestId('operator-facts-work').textContent).toMatch(/Na jakiej podstawie może pracować/)
    expect(screen.getByTestId('operator-facts-work-parameters')).toBeTruthy()
    expect(screen.getByTestId('operator-facts-card-parameters')).toBeTruthy()
    expect(screen.queryByText(/employer_declaration/)).toBeNull()
    expect(screen.queryByText(/Not valid for this employment/i)).toBeNull()
  })

  it('asks for shared evidence only after the issuing country is known', () => {
    const { rerender } = render(
      <OperatorFactsForm
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
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
    expect(screen.queryByTestId('operator-facts-licence-details')).toBeNull()
    expect(screen.queryByTestId('operator-facts-code95-details')).toBeNull()

    rerender(
      <OperatorFactsForm
        countries={[{ value: 'PL', label: 'Polska' }, { value: 'BY', label: 'Białoruś' }]}
        onPatch={() => undefined}
        view={view({
          steps: [
            { key: 'citizenship', visible: true, stored: 'PL' },
            { key: 'stay_basis', visible: false },
            { key: 'work', visible: false },
            { key: 'driving_licence', visible: true, issuing_country: 'PL', categories: ['CE'] },
            { key: 'code95', visible: true, presence: true, evidence_shape: 'shared', asks_file: true },
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
    expect(screen.getByTestId('operator-facts-licence-details')).toBeTruthy()
    expect(screen.getByTestId('operator-facts-code95-details').textContent).toMatch(/Gdzie potwierdzony/)
    expect(screen.queryByText(/Separate evidence/i)).toBeNull()
    expect(screen.queryByText(/driver_license_code95/)).toBeNull()
  })
})
