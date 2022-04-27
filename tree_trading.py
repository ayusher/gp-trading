import numpy as np
from matplotlib import pyplot
import random
import pandas as pd
import pandas_ta as ta
from genetic_trader import Backtest
from pathos.multiprocessing import ProcessingPool as Pool
import time

class GPNode:
    def __init__(self, node_type=None):
        self.parent = None
        self.node_type = node_type
        self.children = []
        self.depth = 0

    def add_child(self, child_node):
        # child_node.depth = self.depth+1
        self.children.append(child_node)
        child_node.parent = self

class GPConstNode(GPNode):
    def __init__(self, value=None):
        super().__init__(node_type="Const")
        self.const_value = value
    
    def evaluate(self, input_state):
        return self.const_value
        
    def pretty_print(self, indents=0, varname=None):
        return str(self.const_value)

    def deepcopy(self):
        new_node = GPConstNode(value=self.const_value)
        new_node.depth = self.depth
        return new_node

    def mutate(self, mutate_rate, mutate_amount):
        if random.random()<mutate_rate: 
            self.const_value += random.uniform(-mutate_amount, mutate_amount)
            return True
        return False

class GPFunctionNode(GPNode):
    def __init__(self, arg_count, func_name=None, gp_function=None):
        super().__init__(node_type="Function")
        self.argument_count = arg_count
        self.gp_function = gp_function
        self.function_name = func_name
        
    def evaluate(self, input_state): 
        assert self.argument_count == len(self.children), \
        'Number of child nodes must match argument count'

        child_results = [c.evaluate(input_state) for c in self.children]
        return self.gp_function(*child_results)

    def pretty_print(self, indents=0, varname = None):
        return self.function_name.join([child.pretty_print() for child in self.children])
        
    def deepcopy(self):
        new_node = GPFunctionNode(self.argument_count, 
                                   self.function_name, 
                                   self.gp_function)
        new_node.depth = self.depth
        
        for child in self.children:
            new_node.add_child(child.deepcopy())
        
        return new_node

    def mutate(self, mutate_rate, mutate_amount):
        out = False
        for i in range(len(self.children)):
            if self.children[i].mutate(mutate_rate, mutate_amount):
                out = True
            elif random.random()<0.05: # regnerate tree randomly
                self.children[i] = generate_random_tree()
                out = True
        return out

class GPTANode(GPNode):
    def __init__(self, func_name=None, gp_function=None, args = []):
        super().__init__(node_type="TA")
        self.gp_function = gp_function
        self.args = args
        self.function_name = func_name
        
    def evaluate(self, input_state): 
        df = input_state['df']
        out = np.array(eval(self.gp_function+"({})".format(*self.args))).tolist()[-1]
        #print(self.gp_function, out)
        return out

    def pretty_print(self, indents=0, varname=None):
        return self.gp_function+"({})".format(*self.args)+".tolist()[-1]"
        
    def deepcopy(self):
        new_node = GPTANode(self.function_name,
                            self.gp_function,
                            [i for i in self.args])
        new_node.depth = self.depth
        
        return new_node

    def mutate(self, mutate_rate, mutate_amount):
        oldargs = [i for i in self.args]
        item = random.randrange(len(self.args))
        if random.random()<mutate_rate:
            self.args[item] = self.args[item] + random.uniform(-mutate_amount, mutate_amount)
        #itemarr = [1 if i==item else 0 for i in range(len(self.args))]
        #self.args = [i+int(random.random()<mutate_rate)*itemarr[]*random.uniform(-mutate_amount, mutate_amount) for i in self.args]
        if oldargs==self.args: return False
        return True


class GPIfNode(GPNode):
    def __init__(self, func_name=None, gp_function=None):
        super().__init__(node_type="Function")
        self.argument_count = 3
        self.gp_function = gp_function
        self.function_name = func_name
        
    def evaluate(self, input_state): 
        assert self.argument_count == len(self.children), \
        'Number of child nodes must match argument count'

        child_results = [c.evaluate(input_state) for c in self.children]
        return self.gp_function(*child_results)

    def pretty_print(self, indents=0, varname = None):
        strout = "("
        if self.argument_count == 3:
            strout += self.children[1].pretty_print(indents+1, varname) + " "
            strout += self.function_name +" " + self.children[0].pretty_print(indents)
            strout += " else "
            strout += self.children[2].pretty_print(indents+1, varname)

        return strout+")"
        
    def deepcopy(self):
        new_node = GPIfNode(self.function_name, 
                            self.gp_function)
        new_node.depth = self.depth
        
        for child in self.children:
            new_node.add_child(child.deepcopy())
        
        return new_node

    def mutate(self, mutate_rate, mutate_amount):
        out = False
        for i in range(len(self.children)):
            if self.children[i].mutate(mutate_rate, mutate_amount):
                out = True
            elif random.random()<0.05: # regnerate tree randomly
                self.children[i] = generate_random_tree()
                out = True
        return out

def generate_random_tree(depth=0):
    global varnum
    choice = random.choices(list(range(3)), weights=[.1, .6, .4], k=1)[0]
    if choice==0 or depth>=5:
        node = GPConstNode(random.uniform(-10, 10))
    elif choice==1:
        func_node = funcs[random.randrange(len(funcs))]()
        for _ in range(func_node.argument_count):
            func_node.add_child(generate_random_tree(depth+1))
        node = func_node
    elif choice==2:
        node = tas[random.randrange(len(tas))]()
    node.depth = depth
    #print(depth)
    return node


def add():
    return GPFunctionNode(arg_count=2, func_name="+", gp_function=lambda x, y: x+y)

def subtract():
    return GPFunctionNode(arg_count=2, func_name="-", gp_function=lambda x, y: x-y)

def multiply():
    return GPFunctionNode(arg_count=2, func_name="*", gp_function=lambda x, y: x*y)

def divide():
    return GPFunctionNode(arg_count=2, func_name="/", gp_function=lambda x, y: x/y if y!=0 else 0)

def rsi():
    return GPTANode(func_name="RSI", gp_function = "df.ta.rsi", args = [random.randrange(50)])

def mfi():
    return GPTANode(func_name="MFI", gp_function = "df.ta.mfi", args = [random.randrange(50)])

def cci():
    return GPTANode(func_name="CCI", gp_function = "df.ta.cci", args = [random.randrange(50)])

def vwma():
    return GPTANode(func_name="VWMA", gp_function = "df.ta.vwma", args = [random.randrange(50)])

def ao():
    return GPTANode(func_name="AO", gp_function = "df.ta.ao", args = [random.randrange(50)])

def mom():
    return GPTANode(func_name="MOM", gp_function = "df.ta.mom", args = [random.randrange(50)])

def sma():
    return GPTANode(func_name="SMA", gp_function = "df.ta.sma", args = [random.randrange(50)])

def if_then():
    return GPIfNode(func_name="if", gp_function=lambda x, y, z: y if x else z)

funcs = [add, subtract, multiply, divide, if_then]
tas = [rsi, mfi, cci, vwma, ao, mom, sma]