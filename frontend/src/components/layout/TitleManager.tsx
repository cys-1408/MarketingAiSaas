import { useEffect } from "react";
import { composeTitle } from "../../brand";

/**
 * Keeps the browser document title branded and route-aware.
 * Renders nothing; call it with the current page label (null for root brand).
 */
export function TitleManager({ page }: { page: string | null }) {
  useEffect(() => {
    document.title = composeTitle(page);
  }, [page]);
  return null;
}
