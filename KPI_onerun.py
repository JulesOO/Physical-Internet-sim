import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import numpy as np

"""
This code calculates KPIs for one simulation and saves graphs in the same folder as the output data
"""

# choose situation to visualize + warm-up period
folder = 'networks/network-europe-volume'
orderfreq_mult = 1
warmup_days = 10

# set standard plot settings
sns.set_style("white")
plt.rc('axes', titlesize=16)
plt.rc('axes', labelsize=12)
plt.rc('xtick', labelsize=10)
plt.rc('ytick', labelsize=10)
plt.rc('legend', fontsize=10)
plt.rcParams["figure.figsize"] = (6,4)

# load data & remove warmup
orders = pd.read_csv(f'{folder}/input/orders.csv')
output_folder = f'{folder}/output/orderfreq_{orderfreq_mult}'
logfile_trucks = f'{output_folder}/transports.csv'
logfile_packages = f'{output_folder}/deliveries.csv'
Transports = pd.read_csv(logfile_trucks)
Transports = Transports.loc[Transports['endtime'] >= warmup_days*24]
Deliveries = pd.read_csv(logfile_packages)
Deliveries = Deliveries.loc[Deliveries['arrivaltime'] >= warmup_days*24]

# calculation
Transports['loadfraction'] = Transports['load']/Transports['capacity']
Deliveries['deliverytime'] = Deliveries['arrivaltime'] - Deliveries['starttime']
Deliveries['order'] = Deliveries['startnode'] + ' > ' + Deliveries['endnode']
Deliveries['delay'] = Deliveries['arrivaltime'] - Deliveries['duetime']
Deliveries['ontime'] = Deliveries['delay'] <= 0

# on-time delivery fraction
ontime_avg = Deliveries['ontime'].mean()
ontime_numsamples = Deliveries['ontime'].count()
ontime_stdev = np.sqrt(ontime_avg*(1-ontime_avg)/ontime_numsamples)
print(f'On-time delivery fraction = {round(ontime_avg*100,2)}[{round((ontime_avg-1.96*ontime_stdev)*100,2)},{round((ontime_avg+1.96*ontime_stdev)*100,2)}]%')

# on-time delivery fraction per order
ontimedf = Deliveries[['order','ontime']].groupby('order',as_index=False).mean()
ontimedf['stdev'] = np.sqrt(ontimedf['ontime']*(1-ontimedf['ontime'])/Deliveries[['order','ontime']].groupby('order',as_index=False).count()['ontime'])
ontimedf = ontimedf.sort_values(by=['ontime'])
print(ontimedf)
plt.figure()
plt.errorbar(ontimedf['order'], ontimedf['ontime'], yerr=1.96*ontimedf['stdev'], fmt='o', capsize=10, markersize=5, markerfacecolor='red', linewidth=2)
plt.title('Estimated: On-time delivery fraction per order (95% CI)')
plt.xlabel('Order')
plt.ylabel('On-time delivery fraction')
plt.xticks(rotation=60,ha='right')
plt.margins(x=0.2)
plt.ylim(ymin=0, ymax=1.1)
plt.tight_layout()
plt.savefig(f'{output_folder}/deliveryfractions.png')

# on-time delivery fraction vs arrival interval
intervals = [int(orders.loc[(orders['source'] == order.split(' > ')[0]) & (orders['target'] == order.split(' > ')[1])]['interval']) for order in ontimedf['order']]
theta = np.polyfit(intervals, ontimedf['ontime'], 1)
y_line = theta[1] + theta[0] * np.array(intervals)
plt.figure()
plt.scatter(intervals,ontimedf['ontime'],label='Order data')
plt.plot(intervals, y_line, 'r',label='Best fit')
plt.title('Estimated: On-time delivery fraction vs mean interarrival time',fontsize=14)
plt.xlabel('Mean order interarrival time (h)')
plt.ylabel('On-time delivery fraction')
plt.ylim(ymin=0, ymax=1.1)
plt.legend(loc=4)
plt.tight_layout()
plt.savefig(f'{output_folder}/interarrival.png')

# total truck driving time
totaltruckdriving = sum(Transports['endtime']-Transports['starttime'])
print(f'\nTotal truck driving time = {totaltruckdriving} hours')

# truck load fraction
loadfraction_avg = Transports['loadfraction'].mean()
print(f'Average truck load fraction = {round(loadfraction_avg*100,2)}%\n')
plt.figure()
plt.hist(Transports['loadfraction'], density=True)
locs, _ = plt.yticks()
plt.yticks(locs,np.round(locs/10,3))
plt.title('Estimated distribution: Truck load fraction')
plt.xlabel('Load Fraction')
plt.ylabel('Density')
plt.tight_layout()
plt.savefig(f'{output_folder}/loadfraction.png')

# delivery time distribution
orders = Deliveries['order'].unique()
for i in range(len(orders)):
    order = orders[i]
    plt.figure()
    plt.hist(Deliveries.loc[Deliveries['order'] == order]['deliverytime'], density=True, bins=10)
    plt.title(f'Estimated distribution: Total delivery time for order {order}',fontsize=12)
    plt.xlabel('Total delivery time (h)')
    plt.ylabel('Density')
    plt.xlim(xmin=0)
    plt.tight_layout()
    plt.savefig(f'{output_folder}/deliverytime_{i}.png')

# time distribution per order (avg abs)
timedist = Deliveries[['order','deliverytime','handlingtime','transporttime']].groupby('order',as_index=False).mean()
timedist['idletime'] = timedist['deliverytime'] - timedist['handlingtime'] - timedist['transporttime']
timedist = timedist[['order','idletime','transporttime','handlingtime']].sort_values(by=['idletime'])
timedist.columns = ['order', 'Idle', 'Transport', 'Handling']
plt.figure(figsize=(8,4))
timedist.plot(x='order', kind='bar', stacked=True)
plt.title('Estimated: Average total delivery time segmentation per order',fontsize=12)
plt.xlabel('Order')
plt.ylabel('Average total delivery time (h)')
plt.xticks(rotation=60,ha='right')
plt.tight_layout()
plt.savefig(f'{output_folder}/timesegmentation.png')

# delay
plt.figure(figsize=(4,5))
plt.hist(Deliveries['delay'], density=True, bins=10)
plt.title('Estimated distribution: Lateness')
plt.ylabel('Density')
plt.xlabel('Lateness (h)')
plt.tight_layout()
plt.savefig(f'{output_folder}/delay.png')