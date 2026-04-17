#ifndef SYSC4906_FLOOD_CELL_HPP_
#define SYSC4906_FLOOD_CELL_HPP_

#include <memory>
#include <unordered_map>
#include <vector>
#include <cadmium/modeling/celldevs/grid/cell.hpp>
#include <cadmium/modeling/celldevs/grid/config.hpp>
#include "flood_state.hpp"

using namespace cadmium::celldevs;

class flood_cell : public GridCell<flood_state, double> {
public:
	flood_cell(const std::vector<int>& id,
			   const std::shared_ptr<const GridCellConfig<flood_state, double>>& config)
		: GridCell<flood_state, double>(id, config) {}

	[[nodiscard]] flood_state localComputation(
		flood_state state,
		const std::unordered_map<std::vector<int>, NeighborData<flood_state, double>>& neighborhood
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
			const bool is_self = std::all_of(
				neighbor_id.begin(), neighbor_id.end(),
				[](int v) { return v == 0; }
			);

			if (!is_self && !n.blocked) {
				max_neighbor_water = std::max(max_neighbor_water, n.water);
			}
		}

		// If a neighbor has more water than us, spread into us
		if (max_neighbor_water > state.water) {
			state.water = max_neighbor_water - 1;
		}
		// Add water at source cell
		if (state.elevation == 0) {
			static int counter = 0;
			if (++counter % 3 == 0 && state.water < 10) {
				state.water = std::min(10, state.water + 1);
			}
		}

		return state;
	}

	[[nodiscard]] double outputDelay(const flood_state& state) const override {
		return 1.0;
	}
};

#endif  // SYSC4906_FLOOD_CELL_HPP_
