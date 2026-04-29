'use strict';

const fs = require('fs');
const path = require('path');

function readStdin() {
	return new Promise((resolve, reject) => {
		let data = '';
		process.stdin.setEncoding('utf8');
		process.stdin.on('data', chunk => {
			data += chunk;
		});
		process.stdin.on('end', () => resolve(data));
		process.stdin.on('error', reject);
	});
}

function normalizeKey(value) {
	return String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
}

function snapshotPokemon(pokemon) {
	return {
		species: String(pokemon.species.name),
		hp: Number(pokemon.hp || 0),
		maxhp: Number(pokemon.maxhp || 0),
		status: String(pokemon.status || ''),
		ability: normalizeKey(pokemon.ability),
		item: normalizeKey(pokemon.item),
		fainted: !!pokemon.fainted || Number(pokemon.hp || 0) <= 0,
		boosts: Object.fromEntries(Object.entries(pokemon.boosts || {}).sort(([a], [b]) => a.localeCompare(b))),
		volatiles: Object.keys(pokemon.volatiles || {}).sort(),
	};
}

function snapshotBattle(battle, turnIndex) {
	return {
		turn: turnIndex,
		sides: [battle.p1, battle.p2].map((side, index) => ({
			name: `p${index + 1}`,
			active: side.active.map(snapshotPokemon),
			side_conditions: Object.keys(side.sideConditions || {}).sort(),
		})),
		weather: String(battle.field.weather || ''),
		terrain: String(battle.field.terrain || ''),
		pseudo_weather: Object.keys(battle.field.pseudoWeather || {}).sort(),
	};
}

function clampStartingHp(pokemon, monData) {
	if (!pokemon || !monData) return;
	const maxhp = Number(pokemon.baseMaxhp || pokemon.maxhp || 0);
	if (!maxhp) return;
	let hp = null;
	if (monData.hp !== undefined && monData.hp !== null) {
		hp = Number(monData.hp);
	} else if (monData.hp_percent !== undefined && monData.hp_percent !== null) {
		hp = Math.floor(maxhp * Math.max(0, Math.min(100, Number(monData.hp_percent))) / 100);
	}
	if (!Number.isFinite(hp) || hp === null) return;
	hp = Math.max(1, Math.min(maxhp, hp));
	pokemon.hp = hp;
}

function sideNeedsChoice(side) {
	if (!side) return false;
	if (side.requestState === 'switch') return true;
	const requestType = side.activeRequest && side.activeRequest.requestType;
	if (requestType === 'switch') return true;
	const forcedSwitch = side.choice && side.choice.forcedSwitch;
	if (Array.isArray(forcedSwitch)) return forcedSwitch.some(Boolean);
	return !!forcedSwitch;
}

function applyPostChoices(battle, choices) {
	if (!choices) return false;
	let applied = false;
	for (const [side, choice] of Object.entries(choices)) {
		if (choice && sideNeedsChoice(battle[side])) {
			battle.choose(side, choice);
			applied = true;
		}
	}
	return applied;
}

async function main() {
	const showdownRoot = process.argv[2];
	if (!showdownRoot) {
		throw new Error('Usage: node showdown_diff_runner.js <showdown-root>');
	}
	const common = require(path.join(showdownRoot, 'test/common'));
	const raw = await readStdin();
	const scenario = JSON.parse(raw);

	const battle = common.createBattle(
		{
			gameType: scenario.gameType || 'singles',
			seed: scenario.seed || 'gen5,99176924e1c86af0',
		},
		[
			scenario.p1.team,
			scenario.p2.team,
		]
	);

	for (const [sideName, teamData] of [['p1', scenario.p1.team], ['p2', scenario.p2.team]]) {
		const side = battle[sideName];
		for (let i = 0; i < (teamData || []).length; i++) {
			clampStartingHp(side.pokemon[i], teamData[i]);
		}
	}

	const snapshots = [snapshotBattle(battle, 0)];
	if (applyPostChoices(battle, scenario.setup_post)) {
		snapshots.push(snapshotBattle(battle, 1));
	}
	for (let i = 0; i < (scenario.turns || []).length; i++) {
		const turn = scenario.turns[i];
		battle.makeChoices(turn.p1, turn.p2);
		applyPostChoices(battle, turn.post);
		snapshots.push(snapshotBattle(battle, snapshots.length));
	}
	process.stdout.write(JSON.stringify(snapshots));
	battle.destroy();
}

main().catch(error => {
	process.stderr.write(`${error && error.stack ? error.stack : String(error)}\n`);
	process.exit(1);
});
