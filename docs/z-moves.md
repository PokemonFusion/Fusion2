# Z-Moves

The 18 generic crystals accept 20 reviewed damaging source pairs in the
[current matrix](design/z-crystals.md). For example **Normalium Z + an actual
active Tackle slot → Breakneck Blitz**, 100-power Physical Normal damage. Eight
selected status sources and 16 signatures are also accepted, with exact native
holders in that matrix. All other source moves remain deferred. These are bounded
routes; holding a crystal does not enable every move of its type.
[Foundation acceptance](testing/z-core-2026-10-23.md) · [special acceptance](testing/z-special-2026-10-23.md).
The [two-source expansion](testing/z-existing-sources-2026-10-25.md) adds
Firium Z/Flamethrower and Waterium Z/Surf, each 175-power Special damage with
a normal single target. Together with eight status sources and16 signatures,
the current registry has44 mappings on34 crystals. Other sources stay deferred.
Ordinary Surf retains its spread targets; its Z copy does not. Flamethrower's
ordinary burn chance is not copied. Current Charizard/Slowpoke level-up data
provides their respective source at level30; actual wild access still requires
an authored source. The local player tests use actual capture/teach/moveset
menus, real purchases, held crystals and the current source slot's PP.

Equip your reusable crystal with `+hold <party slot>=Normalium Z`. During battle:

```
+zmove
+zmove Tackle=B1
+zmove 4=B1
+zmove A2 Tackle=B1
```

The first command shows current choices, real gapped move slots, remaining PP
and side use without choosing an action. Select a displayed slot or full move
name. Doubles require your acting A1/A2 or B1/B2 label. Target labels refer to
current battle slots. `+zmove` queues your one move; wait for the other actors.

Each side gets one activation per battle. Sleep and other normal move
prevention spend no Z use or PP. After the move begins, one source PP is spent,
including under Pressure, immunity or protection. Protect quarters otherwise
effective damage; it does not grant ordinary contact retaliation. The source
move, crystal, species and ability stay yours. Switching, revival and reconnects
do not refill the side use. A new battle starts a fresh budget.

Use native owned party members or your current Fusion in existing human
Wild/Trainer/PvP singles and two-controller doubles. Same-Pokémon Mega/Tera/Z
stacking is unavailable; different allies have separate mechanic budgets.
Holding any Z-Crystal prevents Terastallization. Klutz, Embargo and Magic Room
do not disable activation of the actual matching crystal.

An optional Z-Crystal Counter recipe supplies one of each of the 34 accepted crystals for 10,000 each,
without automatic refill. It must be deliberately installed at a chosen hub;
this change does not add shops or stock to a running world. The published
evidence uses disposable PostgreSQL and production commands with a captured
player transport. Live deployment and socket acceptance are separate.
An existing Counter with an older offer set requires an explicit stock review;
re-running installation rejects drift and does not expand or refill it.

Selected status sources are Splash, Growl, Swords Dance, Haze, Memento, Destiny
Bond, Tailwind and Curse. Their Z bonus occurs before the ordinary base effect;
a blocked base effect keeps a started bonus. Memento prepares one HP-only heal
for that same side/active slot's next conscious incoming holder. Tailwind's
critical bonus lasts until switching; its side timer survives reconnect without
resetting. Curse uses the holder's current Ghost/non-Ghost type when acting.

The source must remain an otherwise legal active move: this PF2 slice gives no
Z exception to Taunt, Disable, Encore, Imprison, choice or Assault Vest. The held
crystal also prevents simultaneously holding a choice item or Assault Vest.
Called sources and unreviewed charging/recharge, variable, multi-hit or spread
combinations are unavailable. Explicit status/signature mappings keep their
reviewed exceptions. A signature uses only its intrinsic effect, not extra
ordinary-source effects. The source's PP history survives reconnects, including
later Spite, and cannot replay as free Z power.

Native Mimikyu may use Mimikium before or after its real Disguise break; both
intact and matching Busted Totem lifecycles are accepted. The seven listed
Pikachu cap forms and both Totem holders have configured ordinary hunt/capture/
teaching proof. Actual live species availability still depends on authored
charts. The [native Necrozma route](necrozma.md) now passes local acceptance:
a real Dusk-Mane pair may use Solganium Z/Sunsteel Strike and a real Dawn-Wings
pair may use Lunalium Z/Moongeist Beam. The same existing signatures, source PP
and side budget apply. The current human controller and both owned sources
are revalidated through reconnect and final sync. Raw fused grants, copied
forms and stale/forged pair proof cannot qualify. Public source includes
`+necrozma`; a running game needs a deliberate release and schema upgrade.
[Released local socket acceptance](testing/necrozma-released-retry-2026-10-24.md)
passed for #831's dated candidate; it does not certify this newer item build or
shared-game deployment. Ultra remains excluded.
