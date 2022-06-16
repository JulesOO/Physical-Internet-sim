import simpy
import networkx as nx
import logging

def protocol_volume(G,env,parameters,nodename):
    """Volume-based protocol

    Parameters
    ----------
    G : NetworkX graph
        The state graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    nodename : str
        Name of the node at which the protocol is running
    """

    logging.debug('%.2f | Node %s | initializing protocol...', env.now, nodename)

    # load parameters
    interval = float(parameters['protocol_interval'])
    truck_storage_capacity = float(parameters['truck_storage_capacity'])

    # initialize node inventory
    node = G.nodes[nodename]['node']
    presort = {nextnode:simpy.PriorityStore(env) for nextnode in G.neighbors(node.name)}
    
    # calculate shortest paths
    _,path = nx.single_source_dijkstra(G, nodename)

    logging.debug('%.2f | Node %s | protocol initialized', env.now, nodename)

    while True:
        
        logging.debug('%.2f | Node %s | checking dispatch rules...', env.now, nodename)

        # sort newly arrived containers based on next destination in shortest path
        for container in node.arrived_containers:
            nextnode = path[container.item[1]][1]
            yield presort[nextnode].put(container)
        node.arrived_containers = []

        # send out trucks
        while True:
            truck = None

            # Rule 1
            if node.available_trucks[0]:
                truck = node.available_trucks[0].pop(0)
                destination = truck.name.split('_')[0]
                logging.debug('%.2f | Node %s | send %s to Node %s: not our truck', env.now, nodename, truck, destination)

            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(presort, key= lambda x: len(presort[x].items)) 
                if len(presort[destination].items) >= truck_storage_capacity:
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)

            if truck:
                cargo = []
                while len(cargo) < truck_storage_capacity and presort[destination].items:
                        container = yield presort[destination].get()
                        cargo.append(container)
                env.process(truck.deliver_cargo(G,node.name,destination,cargo))
            else:
                break
        yield env.timeout(interval)

def protocol_patience(G,env,parameters,nodename,patience):
    """Volume-based protocol + truck driver patience

    Parameters
    ----------
    G : NetworkX graph
        The state graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    nodename : str
        Name of the node at which the protocol is running
    
    patience : float
        Maximum amount of hours a truck driver will wait before returning to their parent node
    """

    logging.debug('%.2f | Node %s | initializing protocol...', env.now, nodename)

    # load parameters
    interval = float(parameters['protocol_interval'])
    truck_storage_capacity = float(parameters['truck_storage_capacity'])

    # initialize node inventory
    node = G.nodes[nodename]['node']
    presort = {nextnode:simpy.PriorityStore(env) for nextnode in G.neighbors(node.name)}
    
    # calculate shortest paths
    _,path = nx.single_source_dijkstra(G, nodename)

    logging.debug('%.2f | Node %s | protocol initialized', env.now, nodename)

    while True:

        logging.debug('%.2f | Node %s | checking dispatch rules...', env.now, nodename)
        
        # sort newly arrived containers based on next destination in shortest path
        for container in node.arrived_containers:
            nextnode =  path[container.item[1]][1]
            yield presort[nextnode].put(container)
        node.arrived_containers = []

        # send out trucks
        while True:
            truck = None

            # Rule 3
            for other_truck in list(node.available_trucks[0]):
                destination = other_truck.name.split('_')[0]
                if len(presort[destination].items) >= truck_storage_capacity:
                    truck = other_truck
                    node.available_trucks[0].remove(truck)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)
                    break
                elif round(env.now-other_truck.idle_since,1) >= patience:
                    truck = other_truck
                    node.available_trucks[0].remove(truck)
                    logging.debug('%.2f | Node %s | send %s to Node %s: not our truck + patience ran out', env.now, nodename, truck, destination)
                    break
            
            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(presort, key= lambda x: len(presort[x].items))
                if len(presort[destination].items) >= truck_storage_capacity: 
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)

            if truck:
                cargo = []
                while len(cargo) < truck_storage_capacity and presort[destination].items:
                        container = yield presort[destination].get()
                        cargo.append(container)
                env.process(truck.deliver_cargo(G,node.name,destination,cargo))
            else:
                break
        yield env.timeout(interval)

def protocol_urgency(G,env,parameters,nodename):
    """Urgency-based protocol

    Parameters
    ----------
    G : NetworkX graph
        The state graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    nodename : str
        Name of the node at which the protocol is running
    """

    logging.debug('%.2f | Node %s | initializing protocol...', env.now, nodename)

    # dispatch deadline calculator
    def dispatch_deadline(nextnode,length,path):
        scale = 1.2
        due_date = presort[nextnode].items[0].priority
        finalnode = presort[nextnode].items[0].item[1]
        delivery_time_estimate = length[finalnode]+2*scale*truck_storage_capacity*handling_time*(len(path[finalnode])-1)
        return due_date-delivery_time_estimate

    ## load parameters
    interval = float(parameters['protocol_interval'])
    truck_storage_capacity = float(parameters['truck_storage_capacity'])
    handling_time = float(parameters['handling_time'])

    ## initialise node inventory
    node = G.nodes[nodename]['node']
    presort = {nextnode:simpy.PriorityStore(env) for nextnode in G.neighbors(node.name)}
    
    ## Calculate shortest paths
    length,path = nx.single_source_dijkstra(G, nodename)

    logging.debug('%.2f | Node %s | protocol initialized', env.now, nodename)

    while True:
        
        logging.debug('%.2f | Node %s | checking dispatch rules...', env.now, nodename)

        # sort newly arrived containers based on next destination in shortest path
        for container in node.arrived_containers:
            nextnode =  path[container.item[1]][1]
            yield presort[nextnode].put(container)
        node.arrived_containers = []

        # send out trucks
        while True:
            truck = None

            # Rule 1
            if node.available_trucks[0]:
                truck = node.available_trucks[0].pop(0)
                destination = truck.name.split('_')[0]
                logging.debug('%.2f | Node %s | send %s to Node %s: not our truck', env.now, nodename, truck, destination)

            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(presort, key= lambda x: len(presort[x].items))
                if len(presort[destination].items) >= truck_storage_capacity:
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)

            # Rule 4
            if not truck and node.available_trucks[1]:
                dispatchdeadline = {x:dispatch_deadline(x,length,path) for x in presort.keys() if presort[x].items}
                if dispatchdeadline and min(dispatchdeadline.values()) - env.now < 0:
                    truck = node.available_trucks[1].pop(0)
                    destination = min(dispatchdeadline, key= lambda x: dispatchdeadline[x])
                    logging.debug('%.2f | Node %s | send %s to Node %s: urgent container delivery', env.now, nodename, truck, destination)

            if truck:
                cargo = []
                while len(cargo) < truck_storage_capacity and presort[destination].items:
                        container = yield presort[destination].get()
                        cargo.append(container)
                env.process(truck.deliver_cargo(G,node.name,destination,cargo))
            else:
                break
        yield env.timeout(interval)

def protocol_information(G,env,parameters,edges,nodename):
    """Volume-based protocol with information about incoming trucks at neighbors

    Parameters
    ----------
    G : NetworkX graph
        The state graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    edges : Pandas DataFrame
        An edge list representation of a graph

    nodename : str
        Name of the node at which the protocol is running
    """

    logging.debug('%.2f | Node %s | initializing protocol...', env.now, nodename)

    # load parameters
    interval = float(parameters['protocol_interval'])
    handling_time = float(parameters['handling_time'])
    truck_storage_capacity = float(parameters['truck_storage_capacity'])

    # initialize node inventory
    node = G.nodes[nodename]['node']
    heaps = {finalnode:simpy.PriorityStore(env) for finalnode in G.nodes}
    heaps.pop(nodename)

    logging.debug('%.2f | Node %s | protocol initialized', env.now, nodename)

    while True:

        logging.debug('%.2f | Node %s | checking dispatch rules...', env.now, nodename)

        # make a copy of graph edges
        H = nx.from_pandas_edgelist(edges, edge_attr=True)

        # edit edge weights with given information
        processing_time = handling_time*truck_storage_capacity
        for nextnode in G.neighbors(node.name):
            estimated_arrival = env.now + G[node.name][nextnode]['weight']
            delaying_trucks = []
            for arrival in G.nodes[nextnode]['node'].incoming_trucks.values():
                if estimated_arrival-processing_time < arrival < estimated_arrival:
                    delaying_trucks.append(arrival)
            if len(delaying_trucks) >= G.nodes[nextnode]['node'].forklifts.capacity:
                first_arrival = min(delaying_trucks)
                min_unavailable = processing_time*(len(delaying_trucks)//G.nodes[nextnode]['node'].forklifts.capacity)
                min_delay = round(first_arrival+min_unavailable-estimated_arrival,2)
                if min_delay>0:
                    H[node.name][nextnode]['weight'] += min_delay

        # calculate shortest paths
        _,path = nx.single_source_dijkstra(H, nodename)

        # assign new containers to heaps based on final destination
        for container in node.arrived_containers:
            finalnode = container.item[1]
            yield heaps[finalnode].put(container)
        node.arrived_containers = []

        # group final node heaps containing items by next node in shortest path
        nextnode_finalnodes = {nextnode:[] for nextnode in G.neighbors(node.name)}
        for finalnode in heaps.keys():
            if heaps[finalnode].items:
                nextnode = path[finalnode][1]
                nextnode_finalnodes[nextnode].append(finalnode)
        
        # send out trucks
        while True:
            truck = None

            # Rule 1
            if node.available_trucks[0]:
                truck = node.available_trucks[0].pop(0)
                destination = truck.name.split('_')[0]
                logging.debug('%.2f | Node %s | send %s to Node %s: not our truck', env.now, nodename, truck, destination)

            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(nextnode_finalnodes, key= lambda dest: sum([len(heaps[x].items) for x in nextnode_finalnodes[dest]]))
                if sum([len(heaps[x].items) for x in nextnode_finalnodes[destination]]) >= truck_storage_capacity:
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)
                    
            if truck:
                cargo = []
                while len(cargo) < truck_storage_capacity and any([heaps[x].items for x in nextnode_finalnodes[destination]]):
                    nonempty_heaps = [x for x in nextnode_finalnodes[destination] if heaps[x].items]
                    finalnode = min(nonempty_heaps, key= lambda x: heaps[x].items[0].priority)
                    container = yield heaps[finalnode].get()
                    cargo.append(container)
                env.process(truck.deliver_cargo(G,node.name,destination,cargo))
            else:
                break
        yield env.timeout(interval)

def protocol_information_urgency(G,env,parameters,edges,nodename):
    """Urgency-based protocol with information about incoming trucks at neighbors

    Parameters
    ----------
    G : NetworkX graph
        The state graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    edges : Pandas DataFrame
        An edge list representation of a graph

    nodename : str
        Name of the node at which the protocol is running
    """
    logging.debug('%.2f | Node %s | initializing protocol...', env.now, nodename)

    # load parameters
    interval = float(parameters['protocol_interval'])
    handling_time = float(parameters['handling_time'])
    truck_storage_capacity = float(parameters['truck_storage_capacity'])

    # initialize node inventory
    node = G.nodes[nodename]['node']
    heaps = {finalnode:simpy.PriorityStore(env) for finalnode in G.nodes}
    heaps.pop(nodename)

    # dispatch deadline calculator
    def dispatch_deadline(finalnode,length,path):
        scale = 1.2
        due_date = heaps[finalnode].items[0].priority
        delivery_time_estimate = length[finalnode]+2*scale*truck_storage_capacity*handling_time*(len(path[finalnode])-1)
        return due_date-delivery_time_estimate

    logging.debug('%.2f | Node %s | protocol initialized', env.now, nodename)

    while True:

        logging.debug('%.2f | Node %s | checking dispatch rules...', env.now, nodename)

        # make a copy of graph edges
        H = nx.from_pandas_edgelist(edges, edge_attr=True)

        # edit edge weights with given information
        processing_time = handling_time*truck_storage_capacity
        for nextnode in G.neighbors(node.name):
            estimated_arrival = env.now + G[node.name][nextnode]['weight']
            delaying_trucks = []
            for arrival in G.nodes[nextnode]['node'].incoming_trucks.values():
                if estimated_arrival-processing_time < arrival < estimated_arrival:
                    delaying_trucks.append(arrival)
            if len(delaying_trucks) >= G.nodes[nextnode]['node'].forklifts.capacity:
                first_arrival = min(delaying_trucks)
                min_unavailable = processing_time*(len(delaying_trucks)//G.nodes[nextnode]['node'].forklifts.capacity)
                min_delay = round(first_arrival+min_unavailable-estimated_arrival,2)
                if min_delay>0:
                    H[node.name][nextnode]['weight'] += min_delay
        
        # calculate shortest paths
        length,path = nx.single_source_dijkstra(H, nodename)

        # assign new containers to heaps based on final destination
        for container in node.arrived_containers:
            finalnode = container.item[1]
            yield heaps[finalnode].put(container)
        node.arrived_containers = []

        # group final node heaps containing items by next node in shortest path
        nextnode_finalnodes = {nextnode:[] for nextnode in G.neighbors(node.name)}
        for finalnode in heaps.keys():
            if heaps[finalnode].items:
                nextnode = path[finalnode][1]
                nextnode_finalnodes[nextnode].append(finalnode)
        
        # send out trucks
        while True:
            truck = None

            # Rule 1
            if node.available_trucks[0]:
                truck = node.available_trucks[0].pop(0)
                destination = truck.name.split('_')[0]
                logging.debug('%.2f | Node %s | send %s to Node %s: not our truck', env.now, nodename, truck, destination)

            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(nextnode_finalnodes, key= lambda dest: sum([len(heaps[x].items) for x in nextnode_finalnodes[dest]]))
                if sum([len(heaps[x].items) for x in nextnode_finalnodes[destination]]) >= truck_storage_capacity:
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)

            # Rule 4      
            if not truck and node.available_trucks[1]:
                dispatchdeadlines_heaps = {x:dispatch_deadline(x,length,path) if heaps[x].items else env.now+1 for x in heaps.keys()}
                dispatchdeadline = {y:min([dispatchdeadlines_heaps[x] for x in nextnode_finalnodes[y]]) for y in nextnode_finalnodes.keys() if nextnode_finalnodes[y]}
                if dispatchdeadline and min(dispatchdeadline.values()) - env.now < 0:
                    truck = node.available_trucks[1].pop(0)
                    destination = min(dispatchdeadline, key= lambda x: dispatchdeadline[x])
                    logging.debug('%.2f | Node %s | send %s to Node %s: urgent container delivery', env.now, nodename, truck, destination)

            if truck:
                cargo = []
                while len(cargo) < truck_storage_capacity and any([heaps[x].items for x in nextnode_finalnodes[destination]]):
                    nonempty_heaps = [x for x in nextnode_finalnodes[destination] if heaps[x].items]
                    finalnode = min(nonempty_heaps, key= lambda x: heaps[x].items[0].priority)
                    container = yield heaps[finalnode].get()
                    cargo.append(container)
                env.process(truck.deliver_cargo(G,node.name,destination,cargo))
            else:
                break
        yield env.timeout(interval)

def protocol_consolidation(G,env,parameters,nodename):
    """Urgency-based protocol that allows sub-optimal routes

    Parameters
    ----------
    G : NetworkX graph
        The state graph of the simulation

    env : SimPy Environment
        The simulation environment of the model

    parameters : Pandas DataFrame
        Parameters of the simulation

    nodename : str
        Name of the node at which the protocol is running
    """

    logging.debug('%.2f | Node %s | initializing protocol...', env.now, nodename)

    # load parameters
    interval = float(parameters['protocol_interval'])
    handling_time = float(parameters['handling_time'])
    truck_storage_capacity = float(parameters['truck_storage_capacity'])

    # initialize node inventory
    node = G.nodes[nodename]['node']
    heaps = {finalnode:simpy.PriorityStore(env) for finalnode in G.nodes}
    heaps.pop(node.name)

    # dispatch deadline calculator
    def dispatch_deadline(finalnode,length,path):
        scale = 1.2
        due_date = heaps[finalnode].items[0].priority
        delivery_time_estimate = length[finalnode]+2*scale*truck_storage_capacity*handling_time*(len(path[finalnode])-1)
        return due_date-delivery_time_estimate

    # calculate shortest paths starting from source
    length,path = nx.single_source_dijkstra(G, node.name)

    # calculate shortest paths starting at each neighbor
    neighbor_pathlen = {nextnode:nx.single_source_dijkstra(G, nextnode)[0] for nextnode in G.neighbors(node.name)}

    # group final node heaps by next node(s) in shortest path(s)
    def allocate_heaps(margin,G=G,node=node,heaps=heaps,neighbor_pathlen=neighbor_pathlen,length=length):
        nextnode_finalnodes = {nextnode:[] for nextnode in G.neighbors(node.name)}
        for finalnode in heaps.keys():
            if heaps[finalnode].items:
                optimal_pathlen = length[finalnode]
                for nextnode in G.neighbors(node.name):
                    if neighbor_pathlen[nextnode][finalnode] + G[node.name][nextnode]['weight'] <= optimal_pathlen + margin:
                        nextnode_finalnodes[nextnode].append(finalnode)
        return nextnode_finalnodes

    logging.debug('%.2f | Node %s | protocol initialized', env.now, nodename)

    while True:

        logging.debug('%.2f | Node %s | checking dispatch rules...', env.now, nodename)

        # assign new containers to heaps based on final destination
        for container in node.arrived_containers:
            finalnode = container.item[1]
            yield heaps[finalnode].put(container)
        node.arrived_containers = []
        
        nextnode_finalnodes_opt = allocate_heaps(0)
        nextnode_finalnodes_margin = allocate_heaps(0.1)

        # send out trucks
        while True:
            truck = None

            # first only check optimal routes
            nextnode_finalnodes = nextnode_finalnodes_opt

            # Rule 1
            if node.available_trucks[0]:
                truck = node.available_trucks[0].pop(0)
                destination = truck.name.split('_')[0]
                logging.debug('%.2f | Node %s | send %s to Node %s: not our truck', env.now, nodename, truck, destination)

            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(nextnode_finalnodes, key= lambda dest: sum([len(heaps[x].items) for x in nextnode_finalnodes[dest]]))
                if sum([len(heaps[x].items) for x in nextnode_finalnodes[destination]]) >= truck_storage_capacity:
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill', env.now, nodename, truck, destination)

            # relax the optimality
            nextnode_finalnodes = nextnode_finalnodes_margin

            # Rule 2
            if not truck and node.available_trucks[1]:
                destination = max(nextnode_finalnodes, key= lambda dest: sum([len(heaps[x].items) for x in nextnode_finalnodes[dest]]))
                if sum([len(heaps[x].items) for x in nextnode_finalnodes[destination]]) >= truck_storage_capacity:
                    truck = node.available_trucks[1].pop(0)
                    logging.debug('%.2f | Node %s | send %s to Node %s: possible to fill with suboptimal flows', env.now, nodename, truck, destination)

            # Rule 4
            if not truck and node.available_trucks[1]:
                dispatchdeadlines_heaps = {x:dispatch_deadline(x,length,path) if heaps[x].items else env.now+1 for x in heaps.keys()}
                dispatchdeadline = {y:min([dispatchdeadlines_heaps[x] for x in nextnode_finalnodes[y]]) for y in nextnode_finalnodes.keys() if nextnode_finalnodes[y]}
                if dispatchdeadline and min(dispatchdeadline.values()) - env.now < 0:
                    truck = node.available_trucks[1].pop(0)
                    destination = min(dispatchdeadline, key= lambda x: dispatchdeadline[x])
                    logging.debug('%.2f | Node %s | send %s to Node %s: urgent container delivery', env.now, nodename, truck, destination)
                    
            if truck:
                cargo = []
                while len(cargo) < truck_storage_capacity and any([heaps[x].items for x in nextnode_finalnodes[destination]]):
                    nonempty_heaps = [x for x in nextnode_finalnodes[destination] if heaps[x].items]
                    finalnode = min(nonempty_heaps, key= lambda x: heaps[x].items[0].priority)
                    container = yield heaps[finalnode].get()
                    cargo.append(container)
                env.process(truck.deliver_cargo(G,node.name,destination,cargo))
            else:
                break
        yield env.timeout(interval)