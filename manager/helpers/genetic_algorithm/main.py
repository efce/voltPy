import numpy as np
# import scipy.io as sio
from genetic_algorithm import geneticAlgorithm


# wczytanie krzywych z pliku txt, krzywe w kolumnach, pierwsza kolumna potencjały
x = np.loadtxt("signals.txt")
# pierwsza kolumna potencjały
x = x[:,1:]

# # wczytanie z pliku mat
# x1 = sio.loadmat("background_1.mat")
# x1 = x1['iis1']
# x1 = x1[:,1:]
# x = x1

# parametry do ustawienia
Pmax = 101       # położenie maksimum pików (trzeba wybrać ręcznie)
Pb = 85          # położenie początku pików (trzeba wybrać ręcznie)
Pe = 116         # położenie końca pików (trzeba wybrać ręcznie)

# parametry dodatkowe (nie trzeba ich zawsze zmieniać)
Popsize = 128    # wielkość populacji - liczba rozwiązań (chromosomów) zakodowanych w populacji
GenNb = 15       # liczba generacji algorytmu
CrossP = 0.9     # prawdopodobieństwo krzyżowania
MutP = 0.05      # prawdopodobieństwo mutacji
pointsBkg = 20   # poczatkowa liczba punktów wybieranych do aproksymacji tła

# procedura aproksymacji tła funkcjami sklejanymi, optymalizowana przez algorytm genetyczny
geneticAlgorithm(x,Pmax,Pb,Pe,Popsize,GenNb,CrossP,MutP,pointsBkg)