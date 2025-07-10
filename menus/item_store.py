from pokemon.utils.enhanced_evmenu import EnhancedEvMenu as EvMenu


def node_start(caller, raw_input=None):
    """Entry point for the store menu."""
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
    room = caller.location
    inv = room.db.store_inventory or {}
    if not raw_input:
        lines = ["|wItems for sale|n"]
        for item, data in inv.items():
            price = data.get("price", 0)
            qty = data.get("quantity", 0)
            lines.append(f"  {item} - ${price} ({qty} in stock)")
        lines.append("Enter '<item> <amount>' to buy or 'back'.")
        text = "\n".join(lines)
        return text, [{"key": "_default", "goto": "node_buy"}]
    cmd = raw_input.strip()
    if cmd.lower() == "back":
        return node_start(caller)
    parts = cmd.split()
    if len(parts) != 2:
        caller.msg("Usage: <item> <amount> or 'back'.")
        return "node_buy", {}
    item, amt = parts[0], parts[1]
    try:
        amt = int(amt)
    except ValueError:
        caller.msg("Amount must be a number.")
        return "node_buy", {}
    data = inv.get(item)
    if not data or data.get("quantity", 0) < amt:
        caller.msg("The store doesn't have that many.")
        return "node_buy", {}
    cost = data.get("price", 0) * amt
    if caller.trainer.money < cost:
        caller.msg("You can't afford that.")
        return "node_buy", {}
    caller.spend_money(cost)
    room.db.store_inventory[item]["quantity"] -= amt
    caller.add_item(item, amt)
    caller.msg(f"You purchase {amt} x {item} for ${cost}.")
    return "node_buy", {}


def node_sell(caller, raw_input=None):
    room = caller.location
    inv = room.db.store_inventory or {}
    if not raw_input:
        lines = ["|wYour inventory|n"]
        for name, qty in caller.inventory.items():
            lines.append(f"  {name} x{qty}")
        lines.append("Enter '<item> <amount>' to sell or 'back'.")
        text = "\n".join(lines)
        return text, [{"key": "_default", "goto": "node_sell"}]
    cmd = raw_input.strip()
    if cmd.lower() == "back":
        return node_start(caller)
    parts = cmd.split()
    if len(parts) != 2:
        caller.msg("Usage: <item> <amount> or 'back'.")
        return "node_sell", {}
    item, amt = parts[0], parts[1]
    try:
        amt = int(amt)
    except ValueError:
        caller.msg("Amount must be a number.")
        return "node_sell", {}
    if not caller.has_item(item, amt):
        caller.msg("You don't have enough of that item.")
        return "node_sell", {}
    price = inv.get(item, {}).get("price", 0) // 2
    total = price * amt
    caller.remove_item(item, amt)
    inv.setdefault(item, {"price": price * 2, "quantity": 0})
    inv[item]["quantity"] += amt
    room.db.store_inventory = inv
    caller.trainer.money += total
    caller.trainer.save()
    caller.msg(f"You sold {amt} x {item} for ${total}.")
    return "node_sell", {}


def node_edit(caller, raw_input=None):
    room = caller.location
    inv = room.db.store_inventory or {}
    if not raw_input:
        lines = ["|wEdit Inventory|n"]
        for item, data in inv.items():
            lines.append(f"  {item} - ${data.get('price',0)} ({data.get('quantity',0)} in stock)")
        lines.append("Commands: add <item> <price> <qty>, price <item> <price>, qty <item> <qty>, del <item>, done")
        text = "\n".join(lines)
        return text, [{"key": "_default", "goto": "node_edit"}]
    parts = raw_input.strip().split()
    if not parts:
        return "node_edit", {}
    cmd = parts[0].lower()
    if cmd == "done":
        room.db.store_inventory = inv
        return node_start(caller)
    if cmd == "add" and len(parts) == 4:
        item, price, qty = parts[1], int(parts[2]), int(parts[3])
        inv[item] = {"price": price, "quantity": qty}
        caller.msg(f"Added {item}.")
    elif cmd == "price" and len(parts) == 3:
        item, price = parts[1], int(parts[2])
        if item in inv:
            inv[item]["price"] = price
            caller.msg("Price updated.")
        else:
            caller.msg("No such item.")
    elif cmd == "qty" and len(parts) == 3:
        item, qty = parts[1], int(parts[2])
        if item in inv:
            inv[item]["quantity"] = qty
            caller.msg("Quantity updated.")
        else:
            caller.msg("No such item.")
    elif cmd == "del" and len(parts) == 2:
        inv.pop(parts[1], None)
        caller.msg("Item removed.")
    else:
        caller.msg("Unknown command.")
    room.db.store_inventory = inv
    return "node_edit", {}


def node_quit(caller, raw_input=None):
    return "Thanks for visiting!", None

