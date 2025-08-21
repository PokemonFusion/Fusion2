from __future__ import annotations

import pprint
import re
from types import SimpleNamespace

import evennia.commands.default.building as building
from django.conf import settings
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

    def format_attributes(self, obj):
        """Return formatted persistent attributes, grouping battle data by ID."""
        attrs = obj.db_attributes.all()

        battle_attrs = {}
        other_attrs = []

        for attr in attrs:
            match = re.match(r"^battle_(\d+)_(.+)$", attr.db_key)
            if match:
                bid = int(match.group(1))
                name = match.group(2)
                battle_attrs.setdefault(bid, []).append((name, attr))
            else:
                other_attrs.append(attr)

        lines = []
        # group battle attributes by id
        for bid in sorted(battle_attrs):
            lines.append(f"Battle {bid}:")
            for name, attr in sorted(battle_attrs[bid], key=lambda itm: itm[0]):
                tmp = SimpleNamespace(
                    db_key=name,
                    db_category=attr.db_category,
                    value=attr.value,
                    strvalue=getattr(attr, "strvalue", None),
                )
                lines.append("  " + self.format_single_attribute(tmp))

        other_lines = sorted(self.format_single_attribute(attr) for attr in other_attrs)
        lines.extend(other_lines)

        if lines:
            return "\n  " + "\n  ".join(lines)
