import { useEffect } from 'react'

type RobotsOptions = {
  index: boolean
  follow: boolean
}

function upsertRobots(content: string) {
  let node = document.head.querySelector('meta[name="robots"]') as HTMLMetaElement | null
  if (!node) {
    node = document.createElement('meta')
    node.setAttribute('name', 'robots')
    node.setAttribute('data-hf-seo', '1')
    document.head.appendChild(node)
  }
  node.setAttribute('content', content)
}

export function useRobotsMeta({ index, follow }: RobotsOptions) {
  useEffect(() => {
    if (typeof document === 'undefined') return
    const content = `${index ? 'index' : 'noindex'},${follow ? 'follow' : 'nofollow'}`
    upsertRobots(content)
  }, [index, follow])
}
