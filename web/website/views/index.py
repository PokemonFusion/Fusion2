"""Project-owned homepage view with Fusion 2 play status context."""

from evennia.web.website.views.index import EvenniaIndexView

from utils.site_status import get_site_status


class Fusion2IndexView(EvenniaIndexView):
    """Homepage view preserving Evennia stats and adding play status."""

    def get_context_data(self, **kwargs):
        """Add display-ready play status to the standard index context."""

        context = super().get_context_data(**kwargs)
        status = get_site_status()
        context.update(
            {
                "site_status": status.status,
                "site_status_label": status.label,
                "site_status_message": status.message,
                "site_status_class": status.css_class,
                "site_logins_enabled": status.logins_enabled,
            }
        )
        return context
