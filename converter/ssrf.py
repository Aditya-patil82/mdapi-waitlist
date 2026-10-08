import ipaddress
import socket
from urllib.parse import urlparse, urljoin
import httpx

MAX_RESPONSE_SIZE = 2 * 1024 * 1024  # 2 MB
MAX_REDIRECTS = 3
FETCH_TIMEOUT = 10.0
DEFAULT_USER_AGENT = "MdAPIBot/0.1 (+https://mdapi.dev/bot)"


class SSRFValidationError(Exception):
    """Raised when URL validation fails SSRF checks."""
    pass


class OversizedResponseError(Exception):
    """Raised when response body exceeds size limit."""
    pass


class InvalidContentTypeError(Exception):
    """Raised when content type is not supported HTML."""
    pass


class MaxRedirectsExceededError(Exception):
    """Raised when redirect limit is exceeded."""
    pass


def is_ip_allowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is a safe public address."""
    # Convert IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1) to IPv4
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    ):
        return False

    # Check for IPv6 Unique Local (fc00::/7) or Link-local (fe80::/10)
    if isinstance(ip, ipaddress.IPv6Address):
        if ip in ipaddress.IPv6Network("fc00::/7") or ip in ipaddress.IPv6Network("fe80::/10"):
            return False

    # Check for IPv4 Link-local / Cloud metadata (169.254.0.0/16)
    if isinstance(ip, ipaddress.IPv4Address):
        if ip in ipaddress.IPv4Network("169.254.0.0/16"):
            return False

    return True


def validate_target_url(url: str) -> None:
    """Validate URL format, scheme, and resolve DNS to prevent SSRF."""
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https are allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")

    # Try parsing directly as an IP address
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if not is_ip_allowed(ip_obj):
            raise SSRFValidationError(f"Access to private/restricted IP '{hostname}' is blocked.")
        return
    except ValueError:
        # Hostname is a domain name, proceed to DNS resolution
        pass

    try:
        addr_info = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise SSRFValidationError(f"Could not resolve hostname '{hostname}': {e}")

    if not addr_info:
        raise SSRFValidationError(f"No IP addresses resolved for hostname '{hostname}'.")

    for entry in addr_info:
        ip_str = entry[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if not is_ip_allowed(ip_obj):
                raise SSRFValidationError(
                    f"Hostname '{hostname}' resolved to blocked IP '{ip_str}'."
                )
        except ValueError:
            raise SSRFValidationError(f"Invalid IP address '{ip_str}' resolved for '{hostname}'.")


async def safe_fetch_html(url: str) -> tuple[str, str]:
    """
    Safely fetches HTML content from the given URL.
    Enforces SSRF validation on every redirect hop, limits response size to 2MB,
    enforces a 10s timeout, and validates HTML content-type.

    Returns:
        tuple[str, str]: (final_resolved_url, html_content_text)
    """
    current_url = url
    redirect_count = 0

    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
    }

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=httpx.Timeout(FETCH_TIMEOUT),
        headers=headers,
    ) as client:
        while True:
            # Validate target URL and resolved IPs before connecting
            validate_target_url(current_url)

            response = await client.get(current_url)

            # Handle redirects manually to enforce SSRF validation on every hop
            if response.is_redirect:
                redirect_count += 1
                if redirect_count > MAX_REDIRECTS:
                    raise MaxRedirectsExceededError(
                        f"Exceeded maximum allowed redirects ({MAX_REDIRECTS})."
                    )

                location = response.headers.get("location")
                if not location:
                    raise SSRFValidationError("Redirect response missing Location header.")

                current_url = urljoin(current_url, location)
                continue

            # Non-redirect response: check HTTP status
            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"Remote server returned HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )

            # Verify Content-Type
            content_type = response.headers.get("content-type", "").lower()
            if not any(t in content_type for t in ("text/html", "application/xhtml+xml", "text/plain")):
                raise InvalidContentTypeError(
                    f"Invalid content type '{content_type}'. Only HTML content is supported."
                )

            # Check Content-Length if provided
            content_length_header = response.headers.get("content-length")
            if content_length_header:
                try:
                    if int(content_length_header) > MAX_RESPONSE_SIZE:
                        raise OversizedResponseError(
                            f"Response size ({content_length_header} bytes) exceeds limit of {MAX_RESPONSE_SIZE} bytes."
                        )
                except ValueError:
                    pass

            # Read response text and enforce size limit
            body_bytes = response.content
            if len(body_bytes) > MAX_RESPONSE_SIZE:
                raise OversizedResponseError(
                    f"Response body ({len(body_bytes)} bytes) exceeds limit of {MAX_RESPONSE_SIZE} bytes."
                )

            return current_url, response.text
