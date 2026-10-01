"""QR code image URL for subscription links."""

from urllib.parse import quote

from config import QR_API_URL


def qr_url(data: str) -> str:
    """Build the QR service URL encoding `data` (the subscription link)."""
    return f"{QR_API_URL}?size=300x300&margin=10&data={quote(data, safe='')}"
