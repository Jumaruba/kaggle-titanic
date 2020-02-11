
import operator 
import math 
import random 
from deap import algorithms 
from deap import gp 
from deap import creator 
from deap import base 
from deap import tools 
import pandas as pd 
import numpy as np

HOWMANYITER = 10

# getting the data
train = pd.read_csv("./data/train.csv") 
test = pd.read_csv("./data/test.csv")
test_2 = pd.read_csv("./data/test.csv")

# we wanna transform this np array in values of 1 and 0 
def sigmoid(arr): 
    return np.round(1. - 1./(1. + np.exp(arr)))

def gp_deap(envolved_train): 

    outputs = envolved_train['Survived'].tolist()
    envolved_train.drop(['Survived', 'PassengerId'], axis = 1, inplace = True)
    inputs = envolved_train.values.tolist()

    def protectedDiv(left, right):
        try:
            return left/right
        except ZeroDivisionError:
            return 1  

    pset = gp.PrimitiveSet("MAIN", len(train.columns))
    pset.addPrimitive(operator.add,2)
    pset.addPrimitive(operator.sub,2)
    pset.addPrimitive(operator.mul,2)
    pset.addPrimitive(protectedDiv, 2) 
    pset.addPrimitive(math.cos,1)
    pset.addPrimitive(math.sin,1)
    pset.addPrimitive(max, 2)
    pset.addPrimitive(min, 2) 
    pset.addEphemeralConstant("rand101", lambda: random.uniform(-10,10)) 

    creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
    creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMin)

    toolbox = base.Toolbox()
    # half of the time is grow tree and the other half is full. Max height = 4
    toolbox.register("expr", gp.genHalfAndHalf, pset = pset,min_ = 1, max_=4) 
    #individual 
    #a individual is a tree, basically. So, we gonna use the iterate method to generate a primitive tree with values of expr
    toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr )
    #Population 
    #population created with the method initRepeat with type list. 
    toolbox.register("population", tools.initRepeat, list, toolbox.individual) 
    toolbox.register("compile", gp.compile, pset = pset )
    
    # We wanna see how relevant the expression is. The value is the actual value that the expression has.   
    def evalSymbReg(individual): 
        # The individual is the expression 
        func = toolbox.compile(expr = individual)
        # The total error is the sum of all errors divided by the number of elements 
        columns = list(train.columns[2:])
        #error 
        return math.fsum(np.round(1- 1.0/(1.0+np.exp(-func(*in_)))) == out for in_, out in zip (inputs,outputs))/len(envolved_train) ,


    toolbox.register("evaluate", evalSymbReg) 
    toolbox.register("select", tools.selTournament, tournsize = 5)
    toolbox.register("mate",gp.cxOnePoint)
    toolbox.register("expr_mut", gp.genFull, min_ = 0, max_ = 4)
    toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

    toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
    toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))

    pop = toolbox.population(n = 300)
    hof = tools.HallOfFame(1) 

    stats_fit = tools.Statistics(lambda ind: ind.fitness.values)
    stats_size = tools.Statistics(len)
    stats = tools.MultiStatistics(fitness = stats_fit, size = stats_fit) 
    stats.register("avg", np.average)
    stats.register("max", np.max)
    stats.register("min", np.min) 
    stats.register("std", np.std)
    pop, log = algorithms.eaSimple(pop, toolbox, 0.5, 0.1, HOWMANYITER, stats=stats,
                                    halloffame=hof, verbose=True)

    #making hof a callable function 
    func2 = toolbox.compile(expr = hof[0]) 

    return func2 

# Cleaning the data 
def cleanData(df): 
    # FILLING NULL VALUES

    #Checking the null values with: print(df.isnull().sum())
    df['Age'] = np.where(df['Age'].isnull(), df['Age'].mean(), df['Age']) 
    df['Embarked'] = np.where(df.Embarked.isnull(), df.Embarked.mode(), df['Embarked']) 
    df['Cabin'] = np.where(df.Cabin.isnull(), 'N', df.Cabin) 
    #Be careful. In Fare we have outliers values. So, it might not be a good idea.... 
    df.Fare = np.where(df.Fare.isnull(), df.Fare.median(), df.Fare)

    # CONVERTING VARIABLES INTO A MANAGEBLE FORMAT (WITH INTEGERS)

    #analysing cabins ----
    
    s = df.Cabin.str
    df.Cabin = np.select([s.contains('A'),s.contains('B'), s.contains('C'), s.contains('D'), s.contains('E'), s.contains('F'), s.contains('G'), s.contains('N'),s.contains('T') ], 
    ['A', 'B', 'C', 'D','E', 'F','G', 'N', 'T'])
    #print(df[['Cabin', 'Survived']].groupby(['Cabin']).mean().to_string())
    
    # after analysing we have
    exp = [df.Cabin == 'D',df.Cabin == 'E',df.Cabin== 'B', df.Cabin == 'C', df.Cabin == 'F',df.Cabin == 'G', df.Cabin == 'A',df.Cabin == 'N', df.Cabin == 'T']
    df.Cabin  = np.select(exp, [4,4,4,3,3,2,2,1,1])

    # analysing sex ----
    df.Sex = np.where(df.Sex == 'female',1,0)
    
    # analysing embarked ----
    # print(df[['Embarked', 'Survived']].groupby('Embarked').mean())
    
    df.Embarked = np.select([df.Embarked == 'C', df.Embarked == 'Q', df.Embarked == 'S'], [3,2,1]) 
    
    # analysing fare ----
    fare = df['Fare']
    df['Fare'] = np.select(
        [np.logical_and(fare > 100, fare <= 200), fare > 200, np.logical_and(fare > 50, fare <= 100),
        np.logical_and(fare > 0, fare <= 50), fare.isnull()], [5, 4, 3, 2, 1])
    
    
    # analysing the ticket ---- 

    ticket = df['Ticket']
    pattern_SC = "^(SC)"
    pattern_A = "^(A)"
    pattern_PC = "^(PC)"
    pattern_STON = "^(SOTON)|^(STON)"
    pattern_length_4 = "^[0-9]{3,4}$"
    pattern_length_5 = "^[0-9]{5}$"
    pattern_length_6 = "^[0-9]{6}$"
    pattern_length_7 = "^[0-9]{7,9}$"
    df['Ticket'] = np.select(
        [ticket.str.contains(pattern_STON, regex=True), ticket.str.contains(pattern_SC, regex=True),
            ticket.str.contains(pattern_A, regex=True),
            ticket.str.contains(pattern_PC, regex=True), ticket.str.contains(pattern_length_4, regex=True),
            ticket.str.contains(pattern_length_5, regex=True),
            ticket.str.contains(pattern_length_6, regex=True), ticket.str.contains(pattern_length_7, regex=True)],
        [3, 6, 1, 8, 5, 7, 4, 2], default=4)

    # analysing age ----

    age = df['Age']
    df['Age'] = np.select([age >= 60, np.logical_and(age < 60, age >= 40), np.logical_and(age < 40, age >= 20),
                                np.logical_and(age >= 7, age < 20), age < 7], [1, 4, 2, 3, 5], default=2)

    # analysing titles ----

    title = df['Name']
    pattern_rev = 'Don|Rev'
    pattern_mr = 'Mr'
    pattern_dr = 'Dr.'
    pattern_master = 'Master'
    pattern_miss = 'Miss.|Ms.'
    pattern_ladies = 'Mlle|Countess|Mme'
    name = df['Name']
    df['Name'] = np.select(
        [name.str.contains(pattern_rev, regex=True), name.str.contains(pattern_mr, regex=True),
         name.str.contains(pattern_dr, regex=True),
         name.str.contains(pattern_master, regex=True), name.str.contains(pattern_miss, regex=True),
         name.str.contains(pattern_ladies, regex=True)], [1, 2, 4, 5, 6, 7], default=3)

    return df 

object_data = cleanData(train)
object_test = cleanData(test)
object_data = gp_deap(object_data)

object_test.drop(['PassengerId'], axis = 1, inplace = True) 
test_array = object_test.values.tolist()
testPrediction = sigmoid(np.array([object_data(*x) for x in test_array]))
result = pd.DataFrame({'PassengerId': test_2['PassengerId'].astype(int), 'Survived': testPrediction.astype(int)})
result.to_csv("genetic_prediction.csv", index = False)