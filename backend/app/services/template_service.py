from jinja2 import Environment

_jinja_env = Environment(autoescape=True)

# Placeholder values a template's Jinja variables get filled with for preview
# purposes only - never a real, clickable tracking link.
PREVIEW_CONTEXT = {
    "first_name": "Jane",
    "tracking_url": "https://tracking.example.test/t/preview",
    "short_url": "https://example.test/s/preview",
    "tracking_pixel": "https://tracking.example.test/t/preview/pixel.gif",
}


def render_template_string(body: str, context: dict[str, str]) -> str:
    return _jinja_env.from_string(body).render(**context)


def render_preview(body: str) -> str:
    return render_template_string(body, PREVIEW_CONTEXT)
