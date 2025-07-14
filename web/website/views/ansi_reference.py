from django.views.generic import TemplateView
from evennia.utils import text2html

class AnsiReferenceView(TemplateView):
    """Display ANSI color codes with search and copy support."""

    template_name = "website/ansi_reference.html"
    page_title = "ANSI Reference"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        codes = [
            ("|r", "Bright red"),
            ("|R", "Dark red"),
            ("|g", "Bright green"),
            ("|G", "Dark green"),
            ("|y", "Bright yellow"),
            ("|Y", "Dark yellow"),
            ("|b", "Bright blue"),
            ("|B", "Dark blue"),
            ("|m", "Bright magenta"),
            ("|M", "Dark magenta"),
            ("|c", "Bright cyan"),
            ("|C", "Dark cyan"),
            ("|w", "Bright white"),
            ("|W", "Grey"),
            ("|x", "Dark grey"),
            ("|X", "Black"),
        ]
        table = []
        for code, label in codes:
            sample = text2html.parse_html(f"{code}Sample|n")
            table.append({"code": code, "label": label, "sample": sample})
        context["codes"] = table
        context["page_title"] = self.page_title
        return context
