#include <iostream>
#include <memory>
#include <string>
#include <typeinfo>
#include <fstream>
#include <sstream>
#include <cadmium/modeling/celldevs/asymm/coupled.hpp>
#include <cadmium/modeling/celldevs/asymm/config.hpp>
#include <cadmium/simulation/logger/csv.hpp>
#include <cadmium/simulation/root_coordinator.hpp>
#include "include/flood_cell.hpp"

using namespace cadmium;
using namespace cadmium::celldevs;

std::shared_ptr<AsymmCell<flood_state, double>> addFloodCell(
	const std::string& cellId,
	const std::shared_ptr<const AsymmCellConfig<flood_state, double>>& cellConfig
) {
	if (cellConfig->cellModel == "flood") {
		return std::make_shared<flood_cell>(cellId, cellConfig);
	}
	throw std::bad_typeid();
}

void removeSepLineIfPresent(const std::string& filename) {
	std::ifstream in(filename);
	if (!in.is_open()) return;

	std::string firstLine;
	std::getline(in, firstLine);

	if (firstLine != "sep=;") {
		return;
	}

	std::ostringstream remaining;
	remaining << in.rdbuf();
	in.close();

	std::ofstream out(filename, std::ios::trunc);
	out << remaining.str();
}

int main(int argc, char** argv) {
	if (argc < 2) {
		std::cout << "Usage: " << argv[0]
				  << " SCENARIO_CONFIG.json [MAX_SIMULATION_TIME(default: 500)]\n";
		return -1;
	}

	const std::string configFilePath = argv[1];
	const double simTime = (argc > 2) ? std::stod(argv[2]) : 500.0;

	auto model = std::make_shared<AsymmCellDEVSCoupled<flood_state, double>>(
		"flood", addFloodCell, configFilePath
	);
	model->buildModel();

	auto rootCoordinator = RootCoordinator(model);
	rootCoordinator.setLogger<CSVLogger>("flood_log.csv", ";");

	rootCoordinator.start();
	rootCoordinator.simulate(simTime);
	rootCoordinator.stop();
	removeSepLineIfPresent("flood_log.csv");

	return 0;
}
