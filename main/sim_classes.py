import simpy
import logging

class Truck():

    def __init__(self, env, name, logfile, maxcapacity, handling_time):
        """Truck class

        Parameters
        ----------
        env : SimPy Environment
            The simulation environment of the model

        name : str
            Name of the truck

        logfile : Logging logger
            Logger for information on truck trips

        maxcapacity : int
            Maximum amount of containers that can fit in a truck

        handling_time: float
            Handling time per container loading/unloading action
        """

        self.env = env
        self.name = name
        self.logfile = logfile
        self.storage = simpy.PriorityStore(env, capacity=maxcapacity)
        self.handling_time = handling_time
        self.idle_since = 0

    def __repr__(self):
        return f'Truck {self.name}'
    
    def __eq__(self, other):
        return self.name == other.name

    def _load(self, cargo):
        """Loads containers from the designated cargo into the truck

        Parameters
        ----------
        cargo : list
            The list of containers to load
        """

        logging.debug('%.2f | %s | load cargo...', self.env.now, self)

        while cargo:
            yield self.env.timeout(self.handling_time)
            container = cargo.pop(0)
            yield self.storage.put(container)

        logging.debug('%.2f | %s | finish loading cargo', self.env.now, self)

    def _unload(self, G, endnode, dispatch_time, departure_time, arrival_time):
        """Unloads containers from the truck's cargo at the destination node

        Parameters
        ----------
        G : NetworkX Graph
            State Graph of the simulation

        endnode : str
            Name of the destination node

        dispatch_time : float
            Time at which the truck was originally dispatched

        departure_time : float
            Time at which the truck departed at the start node

        arrival_time : float
            Time at which the truck arrived at the destination node
        """

        logging.debug('%.2f | %s | unload cargo...', self.env.now, self)

        while self.storage.items:
            yield self.env.timeout(self.handling_time)
            container = yield self.storage.get()

            # add data about handling and driving time to container
            container.item[4] += arrival_time - departure_time
            container.item[5] += departure_time - dispatch_time + self.env.now - arrival_time

            G.nodes[endnode]['node'].receive_container(container)
        
        logging.debug('%.2f | %s | finish unloading cargo', self.env.now, self)

    def deliver_cargo(self, G, startnode, endnode, cargo):
        """Controls the truck during the delivery of a designated cargo. This includes:

        - requesting/releasing a forklift to load/unload the truck
        - loading/unloading the truck
        - driving to the destination

        Parameters
        ----------
        G : NetworkX Graph
            State Graph of the simulation

        startnode : str
            Name of the start node

        endnode : str
            Name of the destination node

        cargo : list
            The list of containers to load
        """

        dispatch_time = self.env.now

        # load the truck
        load = len(cargo)
        if load:
            logging.debug('%.2f | %s | request forklift at Node %s', self.env.now, self, startnode)
            request = G.nodes[startnode]['node'].forklifts.request()
            yield request
            yield self.env.process(self._load(cargo))
            logging.debug('%.2f | %s | release forklift at Node %s', self.env.now, self, startnode)
            G.nodes[startnode]['node'].forklifts.release(request)
        
        logging.debug('%.2f | %s | drive %s => %s...', self.env.now, self, startnode, endnode)

        # add the truck to the incoming trucks
        departure_time = self.env.now
        G.nodes[endnode]['node'].incoming_trucks[self.name] = departure_time + G[startnode][endnode]["weight"]

        # drive to the destination
        yield self.env.timeout(G[startnode][endnode]["weight"])
        arrival_time = self.env.now

        logging.debug('%.2f | %s | finish driving %s => %s', self.env.now, self, startnode, endnode)

        # log the truck transport information
        transport = ','.join([self.name, str(startnode), str(endnode), str(departure_time), str(arrival_time), str(load), str(self.storage.capacity)])
        self.logfile.info('%s', transport)
        
        # unload the truck
        if load:
            logging.debug('%.2f | %s | request forklift at Node %s', self.env.now, self, endnode)
            request = G.nodes[endnode]['node'].forklifts.request()
            yield request
            yield self.env.process(self._unload(G,endnode,dispatch_time,departure_time,arrival_time))
            logging.debug('%.2f | %s | release forklift at Node %s', self.env.now, self, endnode)
            G.nodes[endnode]['node'].forklifts.release(request)

        # make the truck available at the destination
        G.nodes[endnode]['node'].receive_truck(self)

class Node():

    def __init__(self, env, name, forklifts, trucks, logfile):
        """Node class

        Parameters
        ----------
        env : SimPy Environment
            The simulation environment of the model

        name : str
            Name of the node

        forklifts : int
            Number of forklifts at this node

        trucks : list
            List of this node's Truck class instances

        logfile : Logging logger
            Logger for information on arrived containers
        """

        self.env = env
        self.name = name
        self.logfile = logfile
        self.arrived_containers = []
        self.incoming_containers = dict()
        self.available_trucks = [[],trucks] # other nodes' trucks, own trucks
        self.incoming_trucks = dict()
        self.forklifts = simpy.Resource(env, capacity=forklifts)

    def __repr__(self):
        return f'Node {self.name}'
    
    def __eq__(self, other):
        return self.name == other.name

    def receive_container(self, container):
        """Process an arrived container

        Parameters
        ----------
        container : SimPy PriorityItem
            The arrived container
        """

        # increase number of hops
        container.item[6] += 1

        # check if container has arrived at final destination
        if container.item[1] == self.name:

            logging.debug('%.2f | %s | container arrived at final destination', self.env.now, self)

            # log arrival time
            container.item[3] = self.env.now
            
            # generate arrival log
            delivery = ','.join([str(x) for x in [container[0],*container[1]]])
            self.logfile.info('%s', delivery)

        else:

            logging.debug('%.2f | %s | container arrived at intermediate hub', self.env.now, self)
            
            # add container to inventory
            self.arrived_containers.append(container)

    def receive_truck(self, truck):
        """Process an arrived truck

        Parameters
        ----------
        truck : Truck class
            The arrived truck
        """

        logging.debug('%.2f | %s | %s available', self.env.now, self, truck)

        # remove truck from incoming trucks
        self.incoming_trucks.pop(truck.name)

        # reset last known idle time
        truck.idle_since = self.env.now

        # add truck to available trucks at node
        if truck.name.split('_')[0] != self.name:
            self.available_trucks[0].append(truck)
        else:
            self.available_trucks[1].append(truck)