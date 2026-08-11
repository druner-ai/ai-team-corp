from urllib.parse import urlparse, urlunparse


def normalize_url(url: str) -> str:
    """
    Normalize a URL by lowercasing scheme and host, removing fragments,
    and ensuring a trailing slash if the path is empty.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower() if parsed.scheme else ""
    netloc = parsed.netloc.lower() if parsed.netloc else ""
    path = parsed.path or "/"
    query = parsed.query
    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def is_valid_url(url: str) -> bool:
    """Check whether the URL has an allowed scheme (http or https) and a non‑empty host."""
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)
