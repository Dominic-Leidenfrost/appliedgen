# Seed metaphor domains

Each YAML file here is a **style hint** for the Transformer agent — not a fixed template. The Transformer is free to invent new domains; these just seed the diversity (see `PLAN.md` §4.3).

Current seeds:

| File | Strength |
|---|---|
| `pirate_adventure.yaml` | small-team exploration, resource scarcity |
| `medieval_kingdom.yaml` | governance, hierarchy, alliances |
| `fluid_dynamics.yaml` | bottlenecks, propagation, scaling |
| `kitchen.yaml` | throughput under time pressure |
| `ecosystem.yaml` | equilibrium, emergent dynamics, long-term change |
| `sports_league.yaml` | competition, ranking, multi-round strategy |
| `heist_movie.yaml` | planning under uncertainty, specialization |
| `garden.yaml` | slow-cycle problems, neglect vs. attention |
| `video_game.yaml` | skill trees, optionality, multi-path solutions |
| `symphony_orchestra.yaml` | tight coordination under timing, hierarchy with delegated expertise |
| `air_traffic_control.yaml` | real-time prioritization, cascading risk, decisions on incomplete info |
| `archival_library.yaml` | information overload, hidden cross-references, preservation vs. access |
| `mountaineering_expedition.yaml` | resource depletion over time, escalating risk, point-of-no-return calls |
| `theater_production.yaml` | rehearsed structure vs. live improvisation, ensemble vs. star roles |

Adding a new seed: copy any file, fill the same fields, drop it in this folder. The Transformer auto-discovers them.
