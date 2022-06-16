import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

"""
This code calculates and saves the warm-up graph in the same folder as the output data
"""

# choose situation to visualize
folder = 'networks/network-europe-volume'
orderfreq_mult = 1

# set standard plot settings
sns.set_style("white")
plt.rc('axes', titlesize=16)
plt.rc('axes', labelsize=12)
plt.rc('xtick', labelsize=10)
plt.rc('ytick', labelsize=10)
plt.rc('legend', fontsize=10)
plt.rcParams["figure.figsize"] = (10,4)

# load data
output_folder = f'{folder}/output/orderfreq_{orderfreq_mult}'
logfile_trucks = f'{output_folder}/transports.csv'
logfile_packages = f'{output_folder}/deliveries.csv'
parameters = pd.read_csv(f'{folder}/input/parameters.csv')
Transports = pd.read_csv(logfile_trucks)
Deliveries = pd.read_csv(logfile_packages)

# calculate KPIs
Transports['loadfraction'] = Transports['load']/Transports['capacity']
Deliveries['deliverytime'] = Deliveries['arrivaltime'] - Deliveries['starttime']
Deliveries['order'] = Deliveries['startnode'] + ' => ' + Deliveries['endnode']
Deliveries['delay'] = Deliveries['arrivaltime'] - Deliveries['duetime']

# avg time distribution for all orders over time
timedistribution = pd.DataFrame(columns = ['Day','Idle','Transport','Handling'])
for cutoff in range(1,round(max(Deliveries['arrivaltime'])/24)):
    meantimes = Deliveries[['arrivaltime','deliverytime','handlingtime','transporttime']].loc[Deliveries['arrivaltime'] < cutoff*24].mean()
    meantimes['idletime'] = meantimes['deliverytime'] - meantimes['handlingtime'] - meantimes['transporttime']
    timedistribution.loc[timedistribution.shape[0]] = [cutoff,meantimes['idletime'],meantimes['transporttime'],meantimes['handlingtime']]

timedistribution.plot(x='Day', kind='bar', stacked=True,
    title='Estimated: Average delivery time distribution up to certain day')
plt.xticks(range(9,int(parameters['sim_days'])+1,10),range(10,int(parameters['sim_days'])+1,10),rotation=0)
plt.xlabel('Day')
plt.ylabel('Average delivery time (h)')
plt.legend(loc=4)
plt.tight_layout()
plt.savefig(f'{output_folder}/warmup.png')