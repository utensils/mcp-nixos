"""nix.dev documentation source."""

from ..caches import nixdev_cache
from ..config import NIXDEV_BASE_URL, APIError
from ..utils import error


def _search_nixdev(query: str, limit: int) -> str:
    """Search nix.dev documentation via cached Sphinx index."""
    try:
        index = nixdev_cache.get_index()

        docnames = index.get("docnames", [])
        titles = index.get("titles", [])
        terms = index.get("terms", {})

        query_lower = query.lower()
        query_terms = query_lower.split()

        # Score documents by term matches
        scores: dict[int, int] = {}
        for term in query_terms:
            # Exact term match
            if term in terms:
                doc_ids = terms[term]
                if isinstance(doc_ids, list):
                    for doc_id in doc_ids:
                        scores[doc_id] = scores.get(doc_id, 0) + 2

            # Partial term matches
            for index_term, doc_ids in terms.items():
                if term in index_term and term != index_term:
                    if isinstance(doc_ids, list):
                        for doc_id in doc_ids:
                            scores[doc_id] = scores.get(doc_id, 0) + 1

        # Also search titles
        for i, doc_title in enumerate(titles):
            if query_lower in doc_title.lower():
                scores[i] = scores.get(i, 0) + 5  # Title match bonus

        if not scores:
            return f"No nix.dev documentation found matching '{query}'"

        # Sort by score, limit results
        sorted_docs = sorted(scores.items(), key=lambda x: -x[1])[:limit]

        results = [f"Found {len(sorted_docs)} nix.dev docs matching '{query}':\n"]
        for doc_id, _score in sorted_docs:
            if doc_id < len(titles) and doc_id < len(docnames):
                doc_title = titles[doc_id]
                docname = docnames[doc_id]
                url = f"{NIXDEV_BASE_URL}/{docname}"

                results.append(f"* {doc_title}")
                results.append(f"  {url}")
                results.append("")

        return "\n".join(results).strip()
    except APIError as exc:
        return error(str(exc), "API_ERROR")
    except Exception as e:
        return error(str(e))
