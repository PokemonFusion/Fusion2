import json
import learnsets as learnsets

def create_move_tables():
    i = 0
    previous = "!"
    parsed_learnset = {}
    gen = ["7", "8", "9"]
    learnset = learnsets.BattleLearnsets
    for pokemon in learnset:
        if previous in pokemon[:len(previous)] and previous != "porygon" and previous != "kabuto":
            continue
        if "alola" not in pokemon:
            leveledmoves = []
            parsed_learnset.update({pokemon: {}})
            parsed_learnset[pokemon].update({"tutor": []})
            parsed_learnset[pokemon].update({"egg": []})
            parsed_learnset[pokemon].update({"tm": []})
            parsed_learnset[pokemon].update({"level": {}})
            if not learnset[pokemon].get("learnset", None):
                continue
            for move in learnset[pokemon]['learnset']:
                for method in learnset[pokemon]['learnset'][move]:
                    if (method[0] in gen):
                        if ("T" in method):
                            if move in parsed_learnset[pokemon]["tutor"]:
                                continue
                            parsed_learnset[pokemon]["tutor"].append(move)
                        if ("L" in method):
                            if move not in leveledmoves:
                                leveledmoves.append(move)
                                move_level = method[method.find("L") + 1:]
                                try:
                                    parsed_learnset[pokemon]["level"][f"{move_level}"] += f", {move}"
                                except KeyError:
                                    parsed_learnset[pokemon]["level"].update({move_level: move})
                        if ("E" in method):
                            if move in parsed_learnset[pokemon]["egg"]:
                                continue
                            parsed_learnset[pokemon]["egg"].append(move)
                        if ("M" in method):
                            if move in parsed_learnset[pokemon]["tm"]:
                                continue
                            parsed_learnset[pokemon]["tm"].append(move)
            parsed_learnset[pokemon]["level"] = dict(sorted(parsed_learnset[pokemon]["level"].items(), key=lambda item: int(item[0])))
            previous = pokemon
            i += 1
    learnset_text = "pfLearnset = " + json.dumps(parsed_learnset, separators=(',', ':'), indent=4)
    with open("parsed_learnset.py", "w") as f:
        f.write(learnset_text)
    print(f"parse file completed, read though {i} pokemon entries.")

if __name__ == "__main__":
    create_move_tables()
