from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    """Validate that the URL uses an allowed scheme (http/https) and has a netloc.

    Rejects schemes like 'ftp', 'file', 'javascript', etc.
    """
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False
