import numpy as np
from matplotlib import pyplot
import random
import pandas as pd
import pandas_ta as ta
from genetic_trader import Backtest
from pathos.multiprocessing import ProcessingPool as Pool
import time

from tree_trading import *

class GeneticStrategy:
    def __init__(self, assets, interval, tree, mx="max", name="NONE", window=50):
        self.assets = assets
        self.interval = interval
        self.max = mx
        self.name = name
        self.desc = "Using basic RSI and moving average indicators, this model trades dips in AAPL."
        self.market = "equity"
        self.window = window
        self.tree = tree
    
    def trade(self, data, buying_power, assets):
        vardict = {}
        vardict['df'] = data["GLD"]
        # df = vardict['df'] 
        try: out = self.tree.evaluate(vardict)
        except: out = -15
        try:
            if out > 10:
                return {"GLD": ("buy", int((buying_power*5/100)//np.array(data["GLD"]["Close"])[-1]))}
            elif out < -10:
                return {"GLD": ("sell", assets["GLD"][0])}
        except: print(self.tree, out)
        return {}

def mutate(tree, mr, ma):
    treeout = tree.deepcopy()
    out = treeout.mutate(mr, ma)
    if out: return treeout
    return None

def crossover(m, f):
    m1 = m.deepcopy()
    parent = m1
    f1 = f.deepcopy()
    path = []
    nodes = []
    while len(m1.children)>0 and len(f1.children)>0 and len(m1.children)==len(f1.children):
        i = random.randrange(min(len(f1.children), len(m1.children)))
        path.append(i)
        nodes.append((m1, f1))
        m1 = m1.children[i]
        f1 = f1.children[i]

    #print(len(path))
    if len(path)==0:
        return None
    rand = random.randrange(len(path))
    nodes[rand][0].children[path[rand]] = nodes[rand][1].children[path[rand]]
    #parent.pretty_print()
    #m.pretty_print()
    return parent


def genetic_algorithm():
    population_size = 96
    mutate_rate = 0.4
    mutate_amount = 4
    random_death = 0.02
    population = [generate_random_tree() for _ in range(population_size)]
    backtest = Backtest(tickers={"GLD": pd.read_csv("GLD.csv")[:2000]}, interval="1d")
    #print(pd.read_csv("GLD.csv")[2000:].reset_index())
    backtest_test = Backtest(tickers={"GLD": pd.read_csv("GLD.csv")[2000:].reset_index()}, interval="1d")
    g = 0
    while True:
        g+=1
        print("population size", len(population))
        for i in range(population_size-len(population)):
            population.append(generate_random_tree())
        print("-"*20)
        li = []
        names = []
        #population = [i for i in population if random.random()>random_death]
        for genome in population:
            if len(li)==0: names.append(g)
            else: names.append(None)
            li.append(GeneticStrategy(["GLD"], "1d", genome).trade)
        for genome in population[:5]:
            print(genome.pretty_print())
            print()

        print("-"*20)
        pool = Pool(processes=24)
        #names[0] = str(names[0])+"oos"
        results = pool.amap(backtest.run, li, names)
        while not results.ready():
            time.sleep(5)

        scores = results.get()
        names[0] = str(names[0])+"oos"
        pool = Pool(processes=24)
        results_test = pool.amap(backtest_test.run, li, names)

        while not results_test.ready():
            time.sleep(5)

        scores_test = [i[0] for i in results_test.get()]

        temp = list(zip(scores, scores_test, population))
        #print(temp[0])
        #temp = [i for i in temp if (i[0][0]/i[1]-1 < 0.1 if i[1]>0 else False)]
        temp.sort(reverse = True, key=lambda x: x[0][0] ) #- x[0][1]/1000)
        print("best sharpe ratio", temp[0][:2])
        #print()
        #if temp[0][0]!=max(scores):
        #    print(temp)
        newpop = [i[2] for i in temp[:4]]
        for i in range(20):
            if random.random()>random_death: newpop.append(temp[4+i][2])
        print("len newpop", len(newpop))
        a = len(newpop)
        for i in range(a):
            tree2 = mutate(newpop[i], mutate_rate, mutate_amount)
            if tree2 is not None: newpop.append(tree2)

        pairs = [random.choices(list(range(len(newpop))), weights=[x**(1/4) for x in list(range(1, len(newpop)+1))][::-1], k=2) for _ in range(64)]
        for pair in pairs:
            temp = crossover(newpop[pair[0]], newpop[pair[1]])
            if temp is not None: newpop.append(temp)

        #newpop[0].pretty_print()
        population = newpop

# def test_backtest():
#     tree = generate_random_tree()
#     backtest = Backtest(tickers={"AAPL": pd.read_csv("../AAPL_data.csv")}, interval="1d")
#     strategy = GeneticStrategy(["AAPL"], "1d", tree)
#     tree.pretty_print()
#     print(backtest.run(strategy.trade))

if __name__=="__main__":
    genetic_algorithm()
