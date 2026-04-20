#ifndef SYSC4906_FLOOD_STATE_HPP_
#define SYSC4906_FLOOD_STATE_HPP_

#include <iostream>
#include <nlohmann/json.hpp>

struct flood_state {
	int water;      // Water level: 0-10 scale
	int elevation;  // Elevation: 0 (low) or 1 (high)
	int blocked;    // Obstacle: 0 (open) or 1 (wall)

	flood_state() : water(0), elevation(0), blocked(0) {}
};

// operator overload to print cell state as an encoded scalar:
//   -2 = blocked (wall)
//   -1 = elevated terrain (dry)
//    0..10 = water level (works for both normal and elevated flooded cells)
std::ostream& operator<<(std::ostream& os, const flood_state& state) {
	if (state.blocked)               os << -2;
	else if (state.elevation == 1 && state.water == 0) os << -1;
	else                             os << state.water;
	return os;
}

// operator!= overload to compare two flood_state objects
bool operator!=(const flood_state& c1, const flood_state& c2) {
	return c1.water != c2.water || c1.elevation != c2.elevation || c1.blocked != c2.blocked;
}

// parse JSON config to populate flood_state
[[maybe_unused]] void from_json(const nlohmann::json& j, flood_state& s) {
	j.at("water").get_to(s.water);
	j.at("elevation").get_to(s.elevation);
	j.at("blocked").get_to(s.blocked);
}

#endif  // SYSC4906_FLOOD_STATE_HPP_
