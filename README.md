This repository contains an agent-based, Physical Internet simulation.
This simulation was developed during my master's dissertation at Ghent University.

The code should be used in the following way:
1. Make a new folder in `./networks/` for the network you want to simulate. e.g. `./networks/network-example`
2. Make the 4 input files necessary to define this network and the simulation parameters:
   - `./networks/network-example/input/edges.csv`
   - `./networks/network-example/input/nodes.csv`
   - `./networks/network-example/input/orders.csv`
   - `./networks/network-example/input/parameters.csv`
3. Create the output directory: `./networks/network-example/output/`
4. Run `sim.py` with  `./networks/network-example` as folder name to simulate the network and save the output data
5. Run `KPI_warmup.py` to check if the simulation reaches a steady state and to decide which warmup period to use
6. Run `KPI_onerun.py` to calculate and plot all relevant KPIs for one simulation replication
7. Run `KPI_orderfreq.py` to see how the network performs under lower/higher volume