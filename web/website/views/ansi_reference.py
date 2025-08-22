from django.views.generic import TemplateView
from evennia.utils import text2html


class AnsiReferenceView(TemplateView):
	"""Display ANSI color codes with search and copy support."""

	template_name = "website/ansi_reference.html"
	page_title = "ANSI Reference"

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		codes = [
			# formatting
			("|n", "Reset"),
			("|*", "Inverse"),
			("|^", "Blink"),
			("|u", "Underline"),
			("|U", "Stop underline"),
			("|i", "Italic"),
			("|I", "Stop italic"),
			("|s", "Strikethrough"),
			("|S", "Stop strikethrough"),
			# bright foreground colours
			("|r", "Bright red"),
			("|g", "Bright green"),
			("|y", "Bright yellow"),
			("|b", "Bright blue"),
			("|m", "Bright magenta"),
			("|c", "Bright cyan"),
			("|w", "Bright white"),
			("|x", "Dark grey"),
			# dark foreground colours
			("|R", "Dark red"),
			("|G", "Dark green"),
			("|Y", "Dark yellow"),
			("|B", "Dark blue"),
			("|M", "Dark magenta"),
			("|C", "Dark cyan"),
			("|W", "Grey"),
			("|X", "Black"),
			# bright backgrounds
			("|[r", "Bright red background"),
			("|[g", "Bright green background"),
			("|[y", "Bright yellow background"),
			("|[b", "Bright blue background"),
			("|[m", "Bright magenta background"),
			("|[c", "Bright cyan background"),
			("|[w", "Bright white background"),
			("|[x", "Dark grey background"),
			# dark backgrounds
			("|[R", "Dark red background"),
			("|[G", "Dark green background"),
			("|[Y", "Dark yellow background"),
			("|[B", "Dark blue background"),
			("|[M", "Dark magenta background"),
			("|[C", "Dark cyan background"),
			("|[W", "Grey background"),
			("|[X", "Black background"),
		]
		table = []
		for code, label in codes:
			sample = text2html.parse_html(f"{code}Sample|n")
			table.append({"code": code, "label": label, "sample": sample})
		context["codes"] = table
		context["page_title"] = self.page_title
		return context
