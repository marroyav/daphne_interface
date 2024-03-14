import matplotlib.pyplot as plt
import click
import numpy as np
import json 

from os import chdir, listdir
from uproot import recreate
from uproot import open as op
from scipy.optimize import curve_fit

map = {
   '10.73.137.104': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7],
       'hpk': [8, 9, 10, 11, 12, 13, 14, 15],'fbk_value':1060,'hpk_value':1560, 'DacV': [25.6, 25.8]},
   '10.73.137.105': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15],
       'hpk': [17, 19, 20, 22],'fbk_value':1090,'hpk_value':1480, 'DacV': [25.8, 25.7, 25.8]},
   '10.73.137.107': {'apa': 1, 'fbk': [0, 2, 5, 7],
       'hpk': [8, 10, 13, 15],'fbk_value':1090,'hpk_value':1575, 'DacV': [25.8, 25.7]},
   '10.73.137.109': {'apa': 2, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15],
       'hpk': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
           33, 34, 35, 36, 37, 38, 39],'fbk_value':1090,'hpk_value':1585, 'DacV': [25.8, 25.8, 25.7, 25.7, 25.6]},
   '10.73.137.111': {'apa': 3, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
       16, 17, 18, 19, 20, 21, 22, 23],
       'hpk': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39],
       'fbk_value':1085,'hpk_value':1590, 'DacV': [25.7, 25.7, 25.6, 25.8, 25.7]},
   '10.73.137.112': {'apa': 4, 'fbk': [],
       'hpk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18,
           19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 37, 39],
       'fbk_value':0,'hpk_value':1580, 'DacV': [25.8, 25.6, 25.6, 25.9, 25.6]},
   '10.73.137.113': {'apa': 4, 'fbk': [0,2,5,7], 'hpk': [],'fbk_value':1040,'hpk_value':0, 'DacV': [25.6]},
}

def derivative(bias, current):
    x = current
    f = np.log(x[len(x)/4:])
    fpp=np.gradient(np.gradient(f))
    fpp = np.nan_to_num(fpp)    
    nbdv=bias[len(bias)/4:][np.argmax(fpp)]
    return nbdv

def fit_pulse(t, t0, T, A, P):
    x = (np.array(t) - t0+T)/T
    return P+A*np.power(x,3)*np.exp(3*(1-x))

def IV_relative(bias, current):

    b = bias/100
    c = current

    # The fit does not perform well if the files have a small amount of data
    if len(bias)>20:

        # Computing the relative derivative
        der_y = np.gradient(c)
        rel_y = der_y/c
        rel_y = np.nan_to_num(rel_y)

        # Checking if the data doesn't have infinite values
        if np.sort(np.isinf(rel_y))[len(rel_y)-1] == False:

            # Computing a moving avarage with n=2, just to remove some noise
            n = 2
            rel_yma = np.convolve(rel_y, np.ones(n)/n, mode='valid')
            x_ma = b[n-1:]

            n_cut = 5
            pol = (np.poly1d(np.polyfit(np.array(x_ma), np.array(rel_yma), 5)))
            y_pol = pol(x_ma)[n_cut:]
            index = (np.argmax(y_pol)+ n_cut) - 5 # Selecting a position before the peak

            # Applying a movinga avrage with 8 points for the region before the peak, to make it smoother
            if index > 16:
                y_before = np.convolve(rel_yma[:(index)], np.ones(8)/8, mode='valid')
                y = np.concatenate((y_before, rel_yma[index:]))
                index = [num for num in range(len(y)) if y[num] == rel_yma[np.argmax(y_pol) + n_cut]][0] - 5

                x_before = x_ma[8-1:(index)]
                x = np.concatenate((x_before, x_ma[index:]))
            else:
                x = x_ma
                y = rel_yma

            # Choosing boundaries values for the fitting
            if x[index+5] > 5:
                min_guess = x[index]
                max_guess = x[index + 5]
            else:
                min_guess = 0
                max_guess = 5
            x_bias = np.arange(x[index], x[len(x)-1], 0.01)

            # Fit using a pulse shape function
            try:
                popt2,pcov2  = curve_fit(fit_pulse, x[index:],y[index:], bounds = ([min_guess, 0, 0, -1],[max_guess, 100, 100, max(y)]))
                y_fit2 = fit_pulse(x_bias, popt2[0], popt2[1], popt2[2], popt2[3])

                if len(y_fit2) > 1:
                    STATUS = 'GOOD'
                    breakdown = x_bias[np.argmax(y_fit2)]
                    return breakdown*100
                else:
                    return 0

                #plt.plot(b, rel_y, '+', label = 'Raw')
                #plt.plot(x, y, '+', label = 'Filtered' )
                #plt.plot(x_bias, y_fit2, 'k', label = 'Fitting')
                #plt.vlines(breakdown, -1, 4, colors='b', linestyles='dashed', label = 'Breakdown')
                #plt.xlabel('Bias x 100 (DAC)')
                #plt.ylabel('dI/dV (1/I)')
                #plt.legend()
                #plt.show()

            except:
                return 0
        else:
            return 0
    else:
        return 0

@click.command()
@click.option("--dir", default = '../data')
def main(dir):
    chdir(dir)
    folders = sorted(listdir())
    ip = []
    bk = []
    for i in range(len(folders)):
       if len(folders[i]) > 40:
           chdir(dir + '/'+ str(folders[i]))
           files = sorted(listdir())
           ip_address = folders[i][43:len(folders[i])]
           
           fbk = map[ip_address]['fbk']
           hpk = map[ip_address]['hpk']
           convert = map[ip_address]['DacV']
           values = []

           for j in range(len(files)):
               if files[j][len(files[j])-4:] == 'root': 
                   print(folders[i], files[j])
                   root_file = op(files[j])
                   current = root_file["tree/IV/current"].array()
                   bias = root_file["tree/IV/bias"].array()

                   if len(files[j]) == 21:
                       ch = int(files[j][15])
                   else:
                       ch = int(files[j][15:17])
                   breakdown = float(IV_relative(bias,current))
                   bkd2 = float(derivative(bias, current))
                   if breakdown == 0: 
                       breakdown = bkd2
                       print('Warning: Check file', folders[i], files[j])
                   apa = ch//8
                   factor = convert[apa]
                   if ch in fbk: 
                       upper_lim = breakdown + 4.5 *factor
                   if ch in hpk: 
                       upper_lim = breakdown + 3 * factor
                   values.append(upper_lim)
                   
           ip.append(ip_address)
           bk.append(values)

    chdir(dir)
    dir = {}
    for ip in ip:
        i = ip.index(ip)
        dir[ip] =  bk[i]
    with open("bias_map.json", "w") as outfile: 
        json.dump(dir, outfile)
    print('Done')

if __name__ == "__main__":
    main()
	
	
