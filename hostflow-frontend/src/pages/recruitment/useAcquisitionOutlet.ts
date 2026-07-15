import { useOutletContext } from 'react-router-dom'
import type { AcquisitionOutletContext } from './AcquisitionLayout'

export function useAcquisitionOutlet(): AcquisitionOutletContext {
  return useOutletContext<AcquisitionOutletContext>()
}
