from __future__ import annotations

from django.conf import settings
import pprint

import evennia.commands.default.building as building
from evennia.commands.default.building import CmdExamine as DefaultCmdExamine
from evennia.utils import funcparser, utils
from evennia.utils.ansi import raw as ansi_raw

class CmdExamine(DefaultCmdExamine):
    """Enhanced examine using prettyprint."""

    # add alias @exa as requested
    aliases = DefaultCmdExamine.aliases + ["@exa"]

    def format_single_attribute_detail(self, obj, attr):
        """Pretty-print attribute value including type."""
        if not building._FUNCPARSER:
            building._FUNCPARSER = funcparser.FuncParser(
                settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES
            )

        key, category, value = attr.db_key, attr.db_category, attr.value
        valuetype = ""
        if value is None and attr.strvalue is not None:
            value = attr.strvalue
            valuetype = " |B[strvalue]|n"
        typ = self._get_attribute_value_type(value)
        typ = f" |B[type:{typ}]|n{valuetype}" if typ else f"{valuetype}"
        value = pprint.pformat(value, indent=2, width=78)
        value = building._FUNCPARSER.parse(ansi_raw(value), escape=True)
        return (
            f"Attribute {obj.name}/{self.header_color}{key}|n "
            f"[category={category}]{typ}:\n\n{value}"
        )

    def format_single_attribute(self, attr):
        if not building._FUNCPARSER:
            building._FUNCPARSER = funcparser.FuncParser(
                settings.FUNCPARSER_OUTGOING_MESSAGES_MODULES
            )

        key, category, value = attr.db_key, attr.db_category, attr.value
        valuetype = ""
        if value is None and attr.strvalue is not None:
            value = attr.strvalue
            valuetype = " |B[strvalue]|n"
        typ = self._get_attribute_value_type(value)
        typ = f" |B[type: {typ}]|n{valuetype}" if typ else f"{valuetype}"
        value = pprint.pformat(value, indent=2, width=78)
        value = building._FUNCPARSER.parse(ansi_raw(value), escape=True)
        value = utils.crop(value)
        if category:
            return f"{self.header_color}{key}|n[{category}]={value}{typ}"
        else:
            return f"{self.header_color}{key}|n={value}{typ}"
