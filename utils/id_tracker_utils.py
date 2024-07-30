import shelve

class IDTracker:
    def __init__(self, filename='id_tracker.db'):
        self.filename = filename

    def get_next_id(self, category):
        with shelve.open(self.filename) as db:
            if f"{category}_returned" in db and db[f"{category}_returned"]:
                return db[f"{category}_returned"].pop(0)

            if category not in db:
                db[category] = 0
            db[category] += 1
            return db[category]

    def return_id(self, category, id_number):
        with shelve.open(self.filename) as db:
            if f"{category}_returned" not in db:
                db[f"{category}_returned"] = []
            db[f"{category}_returned"].append(id_number)

def get_id_tracker():
    return IDTracker()
