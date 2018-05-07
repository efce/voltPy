import numpy as np 
from .fitness_function import fitnessFunction
from .fit_scaling import fitScaling
from .selection import selectionRouletteWheel
from .new_population import newPopulation
from .crossover_single_point import crossoverSinglePoint
from .mutation_rand import mutationRand
from .best_result import bestResult


def geneticAlgorithm(x, Pmax: int, Pb: int, Pe: int, Popsize=128, GenNb=15, CrossP=0.9, MutP=0.05, pointsBkg=20):

    # sygnały o teraz poziomo
    xt = x.T
    [m,n] = xt.shape

    # Generacja populacji
    pop = np.zeros((Popsize,n))
    for i in range(0,Popsize):
        points = np.random.permutation(n)
        for j in range(0,pointsBkg):
            pop[i,points[j]] = 1

    for gen in range(0,GenNb):
        # funkcja dopasowania (ocena zakodowanych wariantów tła)
        scores = fitnessFunction(pop,xt,Pmax,Pb,Pe)

        # funkcja skalujaca
        expectation = fitScaling(scores,Popsize)

        # selekcja nowej populacji (roulette wheel)
        parents = selectionRouletteWheel(expectation,Popsize)
        # wybór nowej populacji
        pop = newPopulation(parents,pop,Popsize)

        if gen < GenNb:
            # krzyżowanie (single point)
            pop = crossoverSinglePoint(parents,pop,CrossP)

            # mutacja (rand)
            pop = mutationRand(parents,pop,MutP)

        print('Gen = ' + str(gen+1))

    # wybór nalepszego rozwiazania z ostatniej generacji
    bestChromosome = np.argmax(expectation)
    [signalsWithoutBkg,background] = bestResult(pop[bestChromosome,:],xt,Pmax)

    return (signalsWithoutBkg, background)
  