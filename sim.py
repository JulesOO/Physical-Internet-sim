from main.protocols import *
from main.order_generator import order_generator
from main.init_graph import init_graph
from main.init_logger import init_logger
import simpy
import pandas as pd
import os
import shutil
import logging

"""
This script simulates the same network for multiple values of orderfreq_mult
"""

# choose which network to simulate + which multipliers
folder = 'networks/network-test-volume'
orderfreq_values = [0.1,0.3,0.5,0.75,1,1.25,1.5,1.75,2,2.5,3,3.5,4,5]

# load input data
parameters = pd.read_csv(f'{folder}/input/parameters.csv')
nodes = pd.read_csv(f'{folder}/input/nodes.csv')
edges = pd.read_csv(f'{folder}/input/edges.csv')
orders = pd.read_csv(f'{folder}/input/orders.csv')
SIM_TIME = 24*float(parameters['sim_days']) + 1

# print simulation progress
def printdays(env):
    while True:
        yield env.timeout(240)
        print(env.now, f'day {int(env.now/24)} finished')

for orderfreq_mult in orderfreq_values:

    # edit multiplier parameter
    parameters['orderfreq_mult'] = orderfreq_mult

    # create output folder
    output_folder = f'{folder}/output/orderfreq_{orderfreq_mult}'
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
    os.makedirs(output_folder)

    # initialize data collection
    logfile_trucks = init_logger(f'transports_{orderfreq_mult}',f'{output_folder}/transports.csv')
    logfile_packages = init_logger(f'deliveries_{orderfreq_mult}',f'{output_folder}/deliveries.csv')
    logfile_trucks.info('truckname,startnode,endnode,starttime,endtime,load,capacity')
    logfile_packages.info('duetime,startnode,endnode,starttime,arrivaltime,transporttime,handlingtime,hops')

    # initialize debug logger (change level to logging.DEBUG to generate debug lines)
    logfile_debug = f'{output_folder}/debug.log'
    logging.basicConfig(format='%(message)s',filename=logfile_debug, level=logging.INFO)

    # start simulation environment
    env = simpy.Environment()

    # initialize Graph
    G = init_graph(env,parameters,nodes,edges,logfile_trucks,logfile_packages)

    # add order generators to environment
    for idx in range(orders.shape[0]):
        source, target, order_interval = orders.iloc[idx]
        _ = env.process(order_generator(G,env,parameters,source,target,order_interval))

    # add protocol to environment
    for node in list(G):
        _ = env.process(protocol_volume(G,env,parameters,node))

    # add progress logging to environment
    _ = env.process(printdays(env))
    
    print('Starting simulation...')
    env.run(SIM_TIME)
    print('Simulation finished')