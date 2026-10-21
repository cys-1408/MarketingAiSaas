/**
 * Canonical product identity. Every user-facing product reference in the
 * frontend must use the constant below — never a repository path, an internal
 * package name, or an alternate display name.
 *
 * Customer entity names (campaigns, workspaces, sources, products) are data
 * and are deliberately not covered by this constant.
 */
export const BRAND_NAME = "Marketing AI SaaS" as const;

/** Route-specific document title suffix/prefix composition. */
export function composeTitle(page: string | null = null): string {
  return page ? `${page} · ${BRAND_NAME}` : BRAND_NAME;
}
