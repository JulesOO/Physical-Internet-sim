import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

"""
This code calculates KPIs for different simulations of the same network and saves graphs in the same folder as the output data
"""

# choose situation to visualize + warm-up period
folder = 'networks/network-test-volume'
orderfreq_values = [0.1,0.3,0.5,0.75,1,1.25,1.5,1.75,2,2.5,3,3.5,4,5]
warmup_days = 10

# set standard plot settings
sns.set_style("white")
plt.rc('axes', titlesize=16)
plt.rc('axes', labelsize=12)
plt.rc('xtick', labelsize=10)
plt.rc('ytick', labelsize=10)
plt.rc('legend', fontsize=10)
plt.rcParams["figure.figsize"] = (6,4)

fillrates = []
totaltruckdrivingtimes = []
for orderfreq_mult in orderfreq_values:
    output_folder = f'{folder}/output/orderfreq_{orderfreq_mult}'
    logfile_trucks = f'{output_folder}/transports.csv'
    logfile_packages = f'{output_folder}/deliveries.csv'
    Transports = pd.read_csv(logfile_trucks)
    Transports = Transports.loc[Transports['endtime'] >= warmup_days*24]
    Deliveries = pd.read_csv(logfile_packages)
    Deliveries = Deliveries.loc[Deliveries['arrivaltime'] >= warmup_days*24]
    Deliveries['delay'] = Deliveries['arrivaltime'] - Deliveries['duetime']
    fillrates.append(Deliveries[Deliveries['delay'] <= 0].shape[0] / Deliveries.shape[0])
    totaltruckdrivingtimes.append(sum(Transports['endtime']-Transports['starttime']))

plt.plot(orderfreq_values,fillrates,linewidth=1.5)
plt.title('Estimated: Average on-time delivery fraction vs order frequency',fontsize=12)
plt.ylabel('On-time delivery fraction')
plt.xlabel('Order frequency multiplier')
plt.tight_layout()
plt.savefig(f'{folder}/output/orderfreq.png')

plt.figure()
plt.plot(orderfreq_values,totaltruckdrivingtimes,linewidth=1.5)
plt.title('Estimated: Total driving time vs order frequency',fontsize=12)
plt.ylabel('Driving time (h)')
plt.xlabel('Order frequency multiplier')
plt.tight_layout()
plt.savefig(f'{folder}/output/totaldrivetime.png')