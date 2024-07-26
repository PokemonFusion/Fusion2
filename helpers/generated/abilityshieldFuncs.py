def ignoringAbility() within sim/pokemon.ts
    # and in Neutralizing Gas itself within data/abilities.ts
    onSetAbility(ability, target, source, effect):
    if (effect && effect.effectType === "Ability" && effect.name !== "Trace") {
    this.add("-ability", source, effect);
    pass

