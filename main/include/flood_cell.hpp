#ifndef SYSC4906_FLOOD_CELL_HPP_
#define SYSC4906_FLOOD_CELL_HPP_

#include <algorithm>
#include <memory>
#include <string>
#include <unordered_map>
#include <cadmium/modeling/celldevs/asymm/cell.hpp>
#include <cadmium/modeling/celldevs/asymm/config.hpp>
#include "flood_state.hpp"

using namespace cadmium::celldevs;

class flood_cell : public AsymmCell<flood_state, double> {
public:
	flood_cell(const std::string& id,
			   const std::shared_ptr<const AsymmCellConfig<flood_state, double>>& config)
		: AsymmCell<flood_state, double>(id, config) {}

	[[nodiscard]] flood_state localComputation(
		flood_state state,
		const std::unordered_map<std::string, NeighborData<flood_state, double>>& neighborhood
	) const override {
		// Walls block water flow
		if (state.blocked) {
			state.water = 0;
			return state;
		}

		// Simple water spreading: if neighbors have higher water, gain 1 level
		int max_neighbor_water = 0;

		for (const auto& [neighbor_id, neighbor_data] : neighborhood) {
			const auto& n = *(neighbor_data.state);
			if (!n.blocked && n.elevation >= state.elevation) {
				// Water only flows in from neighbors at same or higher elevation (downhill into us)
				max_neighbor_water = std::max(max_neighbor_water, n.water);
			}
		}

		// If a neighbor has more water than us, spread into us
		if (max_neighbor_water > state.water + 1) {
			state.water = max_neighbor_water - 1;
		}

		return state;
	}

	[[nodiscard]] double outputDelay(const flood_state& state) const override {
		return 1.0;
	}
};

#endif  // SYSC4906_FLOOD_CELL_HPP_
