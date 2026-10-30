from types import SimpleNamespace

from menus import item_store


class FakeTrainer:
    def __init__(self, *, money=0, inventory=None, fail_add_money=False):
        self.money = money
        self.inventory = dict(inventory or {})
        self.fail_add_money = fail_add_money

    def add_money(self, amount):
        if self.fail_add_money:
            raise RuntimeError("money save failed")
        self.money += amount

    def has_item(self, name, amount=1):
        return self.inventory.get(name.lower(), 0) >= amount

    def list_inventory(self):
        return [
            SimpleNamespace(item_name=name, quantity=quantity)
            for name, quantity in sorted(self.inventory.items())
        ]


class FakeCaller:
    def __init__(self, trainer, store, *, fail_add_item=False):
        self.trainer = trainer
        self.location = SimpleNamespace(db=SimpleNamespace(store_inventory=store))
        self.fail_add_item = fail_add_item
        self.messages = []

    def msg(self, text):
        self.messages.append(text)

    def spend_money(self, amount):
        if self.trainer.money < amount:
            return False
        self.trainer.money -= amount
        return True

    def add_money(self, amount):
        self.trainer.add_money(amount)

    def add_item(self, name, amount=1):
        if self.fail_add_item:
            raise RuntimeError("inventory save failed")
        key = name.lower()
        self.trainer.inventory[key] = self.trainer.inventory.get(key, 0) + amount

    def remove_item(self, name, amount=1):
        key = name.lower()
        if self.trainer.inventory.get(key, 0) < amount:
            return False
        remaining = self.trainer.inventory[key] - amount
        if remaining:
            self.trainer.inventory[key] = remaining
        else:
            self.trainer.inventory.pop(key, None)
        return True


def test_item_store_buy_rolls_back_money_and_stock_when_inventory_add_fails():
    store = {"Potion": {"price": 100, "quantity": 3}}
    trainer = FakeTrainer(money=500)
    caller = FakeCaller(trainer, store, fail_add_item=True)

    item_store.node_buy(caller, "Potion 2")

    assert trainer.money == 500
    assert caller.location.db.store_inventory["Potion"]["quantity"] == 3
    assert trainer.inventory == {}
    assert caller.messages[-1] == "Something went wrong adding that item; purchase was rolled back."


def test_item_store_sell_restores_item_when_money_add_fails():
    store = {"Potion": {"price": 100, "quantity": 1}}
    trainer = FakeTrainer(money=0, inventory={"potion": 2}, fail_add_money=True)
    caller = FakeCaller(trainer, store)

    item_store.node_sell(caller, "Potion 2")

    assert trainer.money == 0
    assert trainer.inventory == {"potion": 2}
    assert caller.location.db.store_inventory["Potion"]["quantity"] == 1
    assert caller.messages[-1] == "Something went wrong adding money; sale was rolled back."
