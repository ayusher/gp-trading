import yfinance as yf
import numpy as np
import matplotlib.pyplot as plt
import time

class Backtest:
    def __init__(self, tickers, interval, period="max", value=1e5, window=50, keys=None):
        idict = {"1d": 252, "1w": 52, "1m": 113400, "5m": 22680, "15m": 7560, "30m":3780, "1h":1890}
        self.interval = idict[interval]
        self.data = {}
        self.value = value
        self.window = window
        self.dates = None
        minlen = None
        self.data = tickers
    
    def run(self, strategy, name=None):
        startt = time.time()
        portfolio_value = []
        buying_power = self.value
        assets = {}
        totrades = 0
        for ticker in self.data:
            assets[ticker] = [0, 0]
        bought, sold = 0, 0
        poss = {}
        possarr = []
        for j in range(len(self.data[list(self.data.keys())[0]])-self.window-1):
            newdata = {}
            for ticker in self.data:
                newdata[ticker]=self.data[ticker][j:j+self.window]

            actions = strategy(newdata, buying_power, assets) # {ticker: ("buy"/"sell": qty)}
            actionssort = sorted(list(actions.keys()), key=lambda x: actions[x][0]=="buy")
            for ticker in actionssort:
                
                if actions[ticker][0]=="buy":
                    if assets[ticker][0]+actions[ticker][1]>0: 
                        assets[ticker][1]=(assets[ticker][1]*assets[ticker][0]+actions[ticker][1]*self.data[ticker]["Open"][j+self.window])/(assets[ticker][0]+actions[ticker][1])
                    else: assets[ticker][1] = 0
                    if self.data[ticker]["Open"][j+self.window]*actions[ticker][1]>buying_power:
                        actions[ticker] = (actions[ticker][0], int(buying_power/self.data[ticker]["Open"][j+self.window]))
                    assets[ticker][0]+=actions[ticker][1]
                    bought += self.data[ticker]["Open"][j+self.window]*actions[ticker][1]
                    buying_power-=self.data[ticker]["Open"][j+self.window]*actions[ticker][1]
                    if buying_power<0: print("WARNING: NEGATIVE BUYING POWER", buying_power)
                    totrades += 1
                    poss[ticker] = poss.get(ticker, [])+[[j, self.data[ticker]["Open"][j+self.window], actions[ticker][1]]]
                elif actions[ticker][0]=="sell":
                    #print(actions[ticker][1])
                    assets[ticker][0]-=actions[ticker][1]
                    sold += self.data[ticker]["Open"][j+self.window]*actions[ticker][1]
                    buying_power+=self.data[ticker]["Open"][j+self.window]*actions[ticker][1]
                    totrades += 1
                    need_closure = actions[ticker][1]
                    while need_closure>0:
                        if ticker not in poss or len(poss[ticker])==0:
                            poss[ticker] = []
                            need_closure = 0
                        elif need_closure >= poss[ticker][-1][2]:
                            need_closure -= poss[ticker][-1][2]
                            possarr.append([poss[ticker][-1][0], j, poss[ticker][-1][1], self.data[ticker]["Open"][j+self.window], poss[ticker][-1][2], ticker])
                            poss[ticker] = poss[ticker][:-1]
                        else:
                            poss[ticker][-1][2] = poss[ticker][-1][2]-need_closure
                            #need_closure = 0
                            possarr.append([poss[ticker][-1][0], j, poss[ticker][-1][1], self.data[ticker]["Open"][j+self.window], need_closure, ticker])
                            need_closure = 0

            portfolio_value.append(buying_power + sum([assets[ticker][0]*self.data[ticker]["Open"][j+self.window] for ticker in self.data]))
        self.assets = assets
        #print(portfolio_value)
        plt.cla()
        plt.plot(portfolio_value)
        if name is not None: plt.savefig("portfolio_value{}.png".format(name))
        return (self.metrics(portfolio_value, totrades, min(bought, sold)), time.time()-startt) #+[possarr]

    def metrics(self, value, totrades, turnover_amt):
        maxv = value[0]
        mdd = 0
        for v in value:
            if v>=maxv: maxv = v
            elif (v-maxv)/maxv < mdd: 
                mdd = (v-maxv)/maxv
        mdd = -mdd
        total_return = value[-1]/value[0]
        cagr = total_return**(self.interval/len(value))-1
        tempval = [value[x+1]/value[x]-1 for x in range(len(value)-1)]
        if np.std(tempval)==0: sharpe = 0
        else: sharpe = sum(tempval)/len(tempval)/np.std(tempval)
        self.value = 1e5
        return sharpe
