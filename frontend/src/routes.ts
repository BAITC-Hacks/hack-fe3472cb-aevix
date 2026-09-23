export const pages = ['home', 'learning', 'city', 'recommendations', 'skills', 'achievements', 'hr'] as const
export type Page = typeof pages[number]
export function readPage(): Page {
  const route = location.hash.replace(/^#\/?/, '').split('/')[0]
  return pages.includes(route as Page) ? route as Page : 'home'
}
