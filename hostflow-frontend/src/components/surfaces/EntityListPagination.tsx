import { Pagination, type PaginationProps } from '../ui/Pagination'
import type { EntityListPaginationState } from './entityListTypes'

export type EntityListPaginationProps = EntityListPaginationState &
  Pick<PaginationProps, 'className' | 'previousLabel' | 'nextLabel' | 'pageLabel'>

export default function EntityListPagination(props: EntityListPaginationProps) {
  return <Pagination {...props} />
}
