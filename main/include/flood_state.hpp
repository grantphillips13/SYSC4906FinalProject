#ifndef SYSC4906_FLOOD_STATE_HPP_
#define SYSC4906_FLOOD_STATE_HPP_

#include <algorithm>
#include <cmath>
#include <iostream>
#include <nlohmann/json.hpp>

struct flood_state {
	double water;        // Water level (internal as double for fidelity)
	int elevation;       // Elevation: 0 (low) or 1 (high)
	int blocked;         // Obstacle: 0 (open) or 1 (wall)
	int cell_type;       // 0=normal, 1=blocked/house, 2=pond/source, 3=rain
	double rain_amount;  // Optional rain contribution per step
	double source_level; // Optional fixed pond/source base level

	flood_state()
		: water(0.0), elevation(0), blocked(0), cell_type(0), rain_amount(0.0), source_level(0.0) {}
};

// operator overload to print all state fields for multi-panel viewer support
std::ostream& operator<<(std::ostream& os, const flood_state& state) {
	const int water_display = std::clamp(static_cast<int>(std::lround(state.water)), 0, 10);
	os << "<" << water_display << "," << state.elevation << "," << state.blocked << ">";
	return os;
}

// operator!= overload to compare two flood_state objects
bool operator!=(const flood_state& c1, const flood_state& c2) {
	return std::fabs(c1.water - c2.water) > 1e-9
		|| c1.elevation != c2.elevation
		|| c1.blocked != c2.blocked
		|| c1.cell_type != c2.cell_type
		|| std::fabs(c1.rain_amount - c2.rain_amount) > 1e-9
		|| std::fabs(c1.source_level - c2.source_level) > 1e-9;
}

// parse JSON config to populate flood_state
[[maybe_unused]] void from_json(const nlohmann::json& j, flood_state& s) {
	s.water = j.value("water", 0.0);
	s.elevation = j.value("elevation", 0);
	s.blocked = j.value("blocked", 0);
	s.cell_type = j.value("cell_type", s.blocked ? 1 : 0);
	s.rain_amount = j.value("rain_amount", 0.0);
	s.source_level = j.value("source_level", 0.0);
}

#endif  // SYSC4906_FLOOD_STATE_HPP_
