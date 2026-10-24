"""Ordinary character discovery and explicit review for native Necrozma pairs."""

from evennia import Command

from pokemon.services.necrozma import NecrozmaService
from pokemon.services.necrozma_guards import NecrozmaError
from pokemon.services.placement import PlacementError


class CmdNecrozma(Command):
    """Combine or separate your own native Necrozma at a Pokemon Center.

    Usage:
      +necrozma
      +necrozma inspect <host or companion slot/full UUID>
      +necrozma combine <Necrozma slot/UUID>=<Solgaleo or Lunala slot/UUID>/<move slot>
      +necrozma separate <host slot/UUID>
      +necrozma review <request UUID>

    Review exact identities and confirm yes/no. The route is free, needs two
    owned native sources, and reserves the companion until explicit separation.
    Recombining restores saved source PP, including zero; it never refills PP.
    """

    key = "+necrozma"
    locks = "cmd:all()"
    help_category = "Pokemon"

    def func(self):
        """Parse identities, then delegate every mutable decision to the service."""
        from uuid import UUID
        from pokemon.models.necrozma import NecrozmaCombination, NecrozmaOperation
        from pokemon.models.storage import UserStorage

        caller = self.caller
        text = self.args.strip()
        try:
            service = NecrozmaService(caller)
            storage = UserStorage.objects.get(user_id=service.actor_id)
            action, _, args = text.partition(" ")
            if not action:
                lines = ["Native Necrozma combinations: base Necrozma + Solgaleo → Dusk-Mane; "
                         "base Necrozma + Lunala → Dawn-Wings.",
                         "At a Pokemon Center in human form, use +necrozma combine <host>=<companion>/<move slot>.",
                         "Use +necrozma inspect <slot/full UUID>, or +necrozma separate <host>. "
                         "This free route reserves your companion and preserves saved source PP."]
                for pair in NecrozmaCombination.objects.filter(storage=storage).select_related("host", "companion"):
                    lines.append(f"{pair.host.name} ({pair.host_id}) + {pair.companion.name} ({pair.companion_id}, reserved companion).")
                from django.utils import timezone
                for operation in NecrozmaOperation.objects.filter(storage=storage, state="pending", expires_at__gt=timezone.now()).order_by("created_at"):
                    lines.append(f"Pending {operation.action} review: +necrozma review {operation.pk}")
                caller.msg("\n".join(lines))
                return
            if action.lower() == "inspect":
                from pokemon.services.necrozma_guards import current_pair
                from pokemon.services.ownership import fresh_owned

                identifier = service.resolve(storage, args)
                pokemon, pair = fresh_owned(identifier), current_pair(identifier)
                place = pokemon.placement
                lines = [f"{pokemon.name} — {pokemon.species}; UUID {identifier}",
                         f"Location: {place.location_type}" + (f" slot {place.slot}" if place.slot else ""),
                         f"HP {pokemon.current_hp}/{pokemon.get_max_hp()}; status {pokemon.status or 'healthy'}; held {pokemon.held_item or 'nothing'}."]
                if pair:
                    lines.extend([f"Native pair {pair['id']}: host {pair['host_id']}; reserved companion {pair['companion_id']}.",
                                  f"Source slot {pair['move_slot']} is locked; active/saved moveset edits wait until separation. "
                                  "The companion can be inspected and cannot be used independently."])
                else:
                    lines.append("No active native pair.")
                caller.msg("\n".join(lines))
                return
            if action.lower() == "combine":
                host, companion_slot = args.split("=", 1)
                companion, move_slot = companion_slot.rsplit("/", 1)
                operation = service.prepare("combine", host.strip(), companion.strip(), int(move_slot))
            elif action.lower() == "separate":
                operation = service.prepare("separate", args)
            elif action.lower() == "review":
                operation = NecrozmaOperation.objects.get(pk=UUID(args.strip()), storage=storage)
                if operation.state != "pending":
                    raise NecrozmaError("That review is no longer pending.")
            else:
                raise NecrozmaError("Use +necrozma, inspect, combine, separate or review. See help +necrozma.")
            from utils.enhanced_evmenu import EnhancedEvMenu
            from menus import necrozma

            EnhancedEvMenu(caller, necrozma, startnode="node_review",
                start_kwargs={"request_id": str(operation.pk)}, cmd_on_exit=necrozma.close_review)
        except (ValueError, UserStorage.DoesNotExist, NecrozmaOperation.DoesNotExist) as error:
            caller.msg(str(error) if isinstance(error, PlacementError) else
                "Use +necrozma combine <host slot/UUID>=<companion slot/UUID>/<move slot 1–4>, "
                "+necrozma separate <host>, or +necrozma inspect <owned slot/UUID>.")
