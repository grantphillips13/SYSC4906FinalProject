#ifndef SYSC4906_FLOOD_CELL_HPP_
#define SYSC4906_FLOOD_CELL_HPP_

#include <algorithm>
#include <cmath>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include <cadmium/modeling/celldevs/asymm/cell.hpp>
#include <cadmium/modeling/celldevs/asymm/config.hpp>
#include "flood_state.hpp"

using namespace cadmium::celldevs;

class flood_cell : public AsymmCell<flood_state, double> {
public:
	static constexpr int NORMAL_CELL = 0;
	static constexpr int BLOCKED_CELL = 1;
	static constexpr int SOURCE_CELL = 2;
	static constexpr int RAIN_CELL = 3;

	flood_cell(const std::string& id,
			   const std::shared_ptr<const AsymmCellConfig<flood_state, double>>& config)
		: AsymmCell<flood_state, double>(id, config) {}

	[[nodiscard]] bool isBlockedCell(const flood_state& state) const {
		return state.blocked == 1 || state.cell_type == BLOCKED_CELL;
	}

	[[nodiscard]] bool isSourceCell(const flood_state& state) const {
		return state.cell_type == SOURCE_CELL || state.source_level > 0.0;
	}

	[[nodiscard]] bool isRainCell(const flood_state& state) const {
		return state.cell_type == RAIN_CELL || state.rain_amount > 0.0;
	}

	[[nodiscard]] bool isValidFlowNeighbor(
		const flood_state& current,
		const flood_state& neighbor
	) const {
		if (isBlockedCell(neighbor)) {
			return false;
		}
		// Preserve current terrain behavior: no uphill propagation.
		return neighbor.elevation >= current.elevation;
	}

	[[nodiscard]] std::vector<const flood_state*> collectValidNeighbors(
		const flood_state& current,
		const std::unordered_map<std::string, NeighborData<flood_state, double>>& neighborhood
	) const {
		std::vector<const flood_state*> valid;
		valid.reserve(neighborhood.size());

		for (const auto& [neighbor_id, neighbor_data] : neighborhood) {
			if (neighbor_data.state == nullptr) {
				continue;
			}
			const auto& n = *(neighbor_data.state);
			if (isValidFlowNeighbor(current, n)) {
				valid.push_back(&n);
			}
		}

		return valid;
	}

	[[nodiscard]] std::vector<const flood_state*> collectActiveNeighbors(
		const flood_state& current,
		const std::unordered_map<std::string, NeighborData<flood_state, double>>& neighborhood
	) const {
		auto valid = collectValidNeighbors(current, neighborhood);
		std::vector<const flood_state*> active;
		active.reserve(valid.size());

		for (const auto* n : valid) {
			if (n->water > 1e-9 || isSourceCell(*n) || isRainCell(*n)) {
				active.push_back(n);
			}
		}

		return active;
	}

	[[nodiscard]] double computeNormalTransition(
		const flood_state& state,
		const std::vector<const flood_state*>& active_neighbors
	) const {
		double next = state.water;
		for (const auto* n : active_neighbors) {
			double transfer = (n->water - state.water) / 9.0;
			if (transfer > 0.0 && n->elevation > state.elevation) {
				const double slope_drop = static_cast<double>(n->elevation - state.elevation);
				transfer *= (1.0 + 0.25 * slope_drop);
			}
			next += transfer;
		}
		return next;
	}

	[[nodiscard]] double computeSourceTransition(
		const flood_state& state,
		const std::vector<const flood_state*>& valid_neighbors
	) const {
		double next = std::max(0.0, state.source_level);
		for (const auto* n : valid_neighbors) {
			if (n->water > 0.0) {
				next += n->water / 9.0;
			}
		}
		return next;
	}

	[[nodiscard]] double computeBlockedTransition(const flood_state& state) const {
		return state.water;
	}

	[[nodiscard]] double applyRainAndClamp(double next, const flood_state& state) const {
		if (isRainCell(state)) {
			next += state.rain_amount;
		}
		return std::max(0.0, next);
	}

	[[nodiscard]] flood_state localComputation(
		flood_state state,
		const std::unordered_map<std::string, NeighborData<flood_state, double>>& neighborhood
	) const override {
		auto valid_neighbors = collectValidNeighbors(state, neighborhood);
		auto active_neighbors = collectActiveNeighbors(state, neighborhood);

		double next_water = 0.0;
		if (isBlockedCell(state)) {
			next_water = computeBlockedTransition(state);
		} else if (isSourceCell(state)) {
			next_water = computeSourceTransition(state, valid_neighbors);
		} else {
			next_water = computeNormalTransition(state, active_neighbors);
		}

		state.water = applyRainAndClamp(next_water, state);

		return state;
	}

	[[nodiscard]] double outputDelay(const flood_state& state) const override {
		return 1.0;
	}
};

#endif  // SYSC4906_FLOOD_CELL_HPP_
