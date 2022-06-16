import random
import simpy
import logging
import networkx as nx

def order_generator(G,env,parameters,source,target,interval):
    """Generates all container arrivals for one order and populates the incoming_containers attribute.

    Parameters
    ----------
    G : NetworkX Graph
        State Graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    source : str
        Name of the order's source node 

    target : str
        Name of the order's destination node 

    interval : str
        Mean order interarrival time
    """
    # load parameters
    lookahead = float(parameters['lookahead'])
    orderfreq_mult = float(parameters['orderfreq_mult'])

    # calculate shortest path distance
    length,_ = nx.single_source_dijkstra(G, source, target)

    # if there is no lookahead, orders can be directly generated without intermediate storage
    if lookahead == 0:

        while True:
            yield env.timeout(round(random.expovariate(orderfreq_mult/interval),2))
            due = env.now + random.randint(round(3*length),round(8*length))
            container = simpy.PriorityItem(due, [source,target,env.now,0,0,0,-1])
            G.nodes[source]['node'].receive_container(container)

    # else, the order generator must populate the incoming_containers list
    else:

        logging.debug('%.2f | order_generator %s => %s | initializing incoming_containers...', env.now, source, target)

        time = 0
        G.nodes[source]['node'].incoming_containers[target] = []
        while time < lookahead:
            time += round(random.expovariate(orderfreq_mult/interval),2)
            G.nodes[source]['node'].incoming_containers[target].append(time)

        logging.debug('%.2f | order_generator %s => %s | incoming_containers initialized', env.now, source, target)
        logging.debug('%.2f | order_generator %s => %s | activated', env.now, source, target)

        while True:
            nextordertime = G.nodes[source]['node'].incoming_containers[target][0]
            lastordertime = G.nodes[source]['node'].incoming_containers[target][-1]
            logging.debug('%.2f | order_generator %s => %s | next arrival %.2f, last arrival %.2f', env.now, source, target, nextordertime, lastordertime)
            
            if nextordertime-env.now <= lastordertime-(env.now+lookahead):
                yield env.timeout(round(nextordertime-env.now,2))

                logging.debug('%.2f | order_generator %s => %s | generate container', env.now, source, target)
                due = env.now + random.randint(round(3*length),round(8*length))
                container = simpy.PriorityItem(due, [source,target,env.now,0,0,0,-1])
                G.nodes[source]['node'].receive_container(container)
                G.nodes[source]['node'].incoming_containers[target].pop(0)
            
            else:
                yield env.timeout(round(lastordertime-(env.now+lookahead),2))

                logging.debug('%.2f | order_generator %s => %s | add future arrival to incoming_containers', env.now, source, target)
                time = lastordertime + round(random.expovariate(orderfreq_mult/interval),2)
                G.nodes[source]['node'].incoming_containers[target].append(time)