import networkx as nx
from main.sim_classes import Truck, Node
import logging

def init_graph(env,parameters,nodes,edges,logfile_trucks,logfile_containers):
    """Returns a NetworkX State Graph.

    Each node in the State Graph has two attributes:
    'node': An instance of the Node class
    'trucks': A list of Truck class instances

    Parameters
    ----------
    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    nodes : Pandas DataFrame
        Each line contains the nodes' parameters

    edges : Pandas DataFrame
        An edge list representation of a graph

    logfile_trucks : Logging logger
        Logger for information on truck trips

    logfile_containers : Logging logger
        Logger for information on arrived containers
    """

    logging.debug('%.2f | init_graph | initializing state graph...', env.now)

    ## load parameters
    truck_max_capacity = int(parameters['truck_storage_capacity'])
    handling_time = float(parameters['handling_time'])

    ## build graph from edge df
    G = nx.from_pandas_edgelist(edges, edge_attr=True)

    ## initialize classes in state graph
    for idx in range(nodes.shape[0]):
        name,_,_,numforklifts,numtrucks = nodes.iloc[idx]
        trucks = [Truck(env,f'{name}_{x}',logfile_trucks,truck_max_capacity,handling_time) for x in range(int(numtrucks))]
        G.nodes[name]['trucks'] = trucks
        G.nodes[name]['node'] = Node(env,name,numforklifts,trucks,logfile_containers)

    logging.debug('%.2f | init_graph | state graph initialized', env.now)

    return G