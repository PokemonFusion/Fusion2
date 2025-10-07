"""EVMenu nodes powering the in-game item store."""

"""EVMenu nodes powering the in-game item store."""

from __future__ import annotations

from typing import Dict, Tuple


def _normalize_store_key(store: Dict[str, Dict[str, int]], name: str) -> Tuple[str | None, Dict[str, int] | None]:
    """Return the matching key/data pair for ``name`` in ``store`` ignoring case."""

    target = name.lower()
    for key, data in store.items():
        if key.lower() == target:
            return key, data
    return None, None


def _parse_item_command(command: str) -> Tuple[str | None, int | None]:
    """Split an '<item> <amount>' command allowing spaces in the item name."""

    parts = command.rsplit(" ", 1)
    if len(parts) != 2:
        return None, None
    item, amount_text = parts[0].strip(), parts[1].strip()
    if not item or not amount_text:
        return None, None
    try:
        amount = int(amount_text)
    except ValueError:
        return item, None
    return item, amount


def node_start(caller, raw_input=None):
    """Entry point for the item store menu."""

    room = caller.location
    if not room or not room.db.is_item_shop:
        caller.msg("There is no store here.")
        return None, None

    text = "Welcome to the item store."
    options = [
        {"desc": "Buy items", "goto": "node_buy"},
        {"desc": "Sell items", "goto": "node_sell"},
    ]
    if caller.check_permstring("Builders"):
        options.append({"desc": "Edit inventory", "goto": "node_edit"})
    options.append({"key": ("quit", "q"), "desc": "Leave", "goto": "node_quit"})
    return text, options


def node_buy(caller, raw_input=None):
    """Handle purchasing items from the store."""

    room = caller.location
    store = room.db.store_inventory or {}
    trainer = getattr(caller, "trainer", None)
    if not trainer:
        caller.msg("You have no trainer record.")
        return node_start(caller)

    if not raw_input:
        lines = ["|wItems for sale|n"]
        for item, data in store.items():
            price = data.get("price", 0)
            qty = data.get("quantity", 0)
            lines.append(f"  {item} - ${price} ({qty} in stock)")
        lines.append("Enter '<item> <amount>' to buy or 'back'.")
        text = "\n".join(lines)
        return text, [{"key": "_default", "goto": "node_buy"}]

    command = raw_input.strip()
    if command.lower() == "back":
        return node_start(caller)

    item_name, amount = _parse_item_command(command)
    if not item_name or amount is None:
        caller.msg("Usage: <item> <amount> or 'back'.")
        return node_buy(caller)
    if amount <= 0:
        caller.msg("You must purchase at least one item.")
        return node_buy(caller)

    store_key, data = _normalize_store_key(store, item_name)
    if not data or data.get("quantity", 0) < amount:
        caller.msg("The store doesn't have that many.")
        return node_buy(caller)

    cost = data.get("price", 0) * amount
    if not caller.spend_money(cost):
        caller.msg("You can't afford that.")
        return node_buy(caller)

    data["quantity"] = max(0, data.get("quantity", 0) - amount)
    store[store_key] = data
    room.db.store_inventory = store
    caller.add_item(store_key, amount)
    caller.msg(f"You purchase {amount} x {store_key} for ${cost}.")
    return node_buy(caller)


def node_sell(caller, raw_input=None):
    """Handle selling items back to the store."""

    room = caller.location
    store = room.db.store_inventory or {}
    trainer = getattr(caller, "trainer", None)
    if not trainer:
        caller.msg("You have no trainer record.")
        return node_start(caller)

    if not raw_input:
        lines = ["|wYour inventory|n"]
        for entry in trainer.list_inventory():
            lines.append(f"  {entry.item_name.title()} x{entry.quantity}")
        lines.append("Enter '<item> <amount>' to sell or 'back'.")
        text = "\n".join(lines)
        return text, [{"key": "_default", "goto": "node_sell"}]

    command = raw_input.strip()
    if command.lower() == "back":
        return node_start(caller)

    item_name, amount = _parse_item_command(command)
    if not item_name or amount is None:
        caller.msg("Usage: <item> <amount> or 'back'.")
        return node_sell(caller)
    if amount <= 0:
        caller.msg("You must sell at least one item.")
        return node_sell(caller)

    if not trainer.has_item(item_name, amount):
        caller.msg("You don't have enough of that item.")
        return node_sell(caller)

    store_key, data = _normalize_store_key(store, item_name)
    price = (data or {}).get("price", 0) // 2
    total = price * amount

    if not caller.remove_item(item_name, amount):
        caller.msg("Something went wrong removing that item.")
        return node_sell(caller)

    if store_key is None:
        store_key = item_name
        data = {"price": price * 2, "quantity": 0}
    data.setdefault("price", price * 2)
    data["quantity"] = data.get("quantity", 0) + amount
    store[store_key] = data
    room.db.store_inventory = store

    trainer.add_money(total)
    caller.msg(f"You sold {amount} x {store_key} for ${total}.")
    return node_sell(caller)


def node_edit(caller, raw_input=None):
    """Administrative inventory editor."""

    room = caller.location
    store = room.db.store_inventory or {}
    if not raw_input:
        lines = ["|wEdit Inventory|n"]
        for item, data in store.items():
            lines.append(f"  {item} - ${data.get('price', 0)} ({data.get('quantity', 0)} in stock)")
        lines.append(
            "Commands: add <item> <price> <qty>, price <item> <price>, qty <item> <qty>, del <item>, done"
        )
        text = "\n".join(lines)
        return text, [{"key": "_default", "goto": "node_edit"}]

    parts = raw_input.strip().split()
    if not parts:
        return node_edit(caller)

    command = parts[0].lower()
    if command == "done":
        room.db.store_inventory = store
        return node_start(caller)

    if command == "add" and len(parts) == 4:
        item = parts[1]
        try:
            price, qty = int(parts[2]), int(parts[3])
        except ValueError:
            caller.msg("Price and quantity must be numbers.")
            return node_edit(caller)
        store[item] = {"price": price, "quantity": qty}
        caller.msg(f"Added {item}.")
    elif command == "price" and len(parts) == 3:
        item = parts[1]
        try:
            price = int(parts[2])
        except ValueError:
            caller.msg("Price must be a number.")
            return node_edit(caller)
        if item in store:
            store[item]["price"] = price
            caller.msg("Price updated.")
        else:
            caller.msg("No such item.")
    elif command == "qty" and len(parts) == 3:
        item = parts[1]
        try:
            qty = int(parts[2])
        except ValueError:
            caller.msg("Quantity must be a number.")
            return node_edit(caller)
        if item in store:
            store[item]["quantity"] = qty
            caller.msg("Quantity updated.")
        else:
            caller.msg("No such item.")
    elif command == "del" and len(parts) == 2:
        store.pop(parts[1], None)
        caller.msg("Item removed.")
    else:
        caller.msg("Unknown command.")

    room.db.store_inventory = store
    return node_edit(caller)


def node_quit(caller, raw_input=None):
    """Exit the menu."""

    return "Thanks for visiting!", None
