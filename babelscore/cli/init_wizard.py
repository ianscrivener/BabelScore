from urllib.parse import urlparse
import httpx
from rich.console import Console

console = Console()


def slug_from_url(base_url: str) -> str:
    """Extract hostname from base_url to use as provider cache key."""
    return urlparse(base_url).hostname or base_url


def fetch_models(base_url: str, api_key: str) -> list[str] | None:
    """Fetch model list from /v1/models. Returns list or None on any failure."""
    url = base_url.rstrip("/") + "/models"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=5.0,
        )
    except Exception as exc:
        console.print(f"[red]Model fetch failed:[/red] {exc}")
        return None

    if response.status_code != 200:
        console.print(f"[red]Model fetch returned {response.status_code}[/red]")
        return None

    data = response.json().get("data", [])
    models = [m["id"] for m in data if "id" in m]
    if not models:
        console.print("[yellow]Provider returned no models.[/yellow]")
        return None

    return models
