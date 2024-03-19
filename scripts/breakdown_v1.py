import matplotlib.pyplot as plt
import click
import numpy as np
import json 

from os import chdir, listdir
from uproot import recreate
from uproot import open as op
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter

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

def fit_pulse(t, t0, T, A, P):
    x = (np.array(t) - t0+T)/T
    return P+A*np.power(x,3)*np.exp(3*(1-x))

def IV_PulseShape(bias, current, steps):
    
    b = bias/100
    c = current

    # The fit does not perform well if the files have a small amount of data
    if len(bias)>10:

        # Computing the relative derivative
        der_y = np.gradient(c)
        rel_y = der_y/c
        rel_y = np.nan_to_num(rel_y)
        
        # Checking if the data doesn't have infinite values
        if np.sort(np.isinf(rel_y))[len(rel_y)-1] == False:

            # Filter with n=2, just to remove some noise
            n = 2            
            y = savgol_filter(rel_y, n, 1)  

            # The breakdown voltage seems to be always after the second half of the plot
            n_cut = int(len(b)/2)
            peak = savgol_filter(rel_y, 3*steps, 2)[n_cut:]
            print(peak)
            index = (np.argmax(peak) + n_cut) - 3 #3 is an arbitrary constant that can be changed according with the amount of data
            
            # Choosing boundaries values for the fitting  
            delta = len(b) - index
            if delta > 5 and index > 5:
                min_guess = b[index - 6]
                max_guess = b[index + 5] 
            if delta < 5 and index > 5:
                min_guess = b[index - int(delta/2)]
                max_guess = b[index + int(delta/2)] 
            #if index < 5:
            #    min_guess = b[0]
            #    max_guess = b[index + 5] 

            # Fit using a pulse shape function
            x_bias = np.arange(min_guess, b[len(b)-1], 0.01)
            try:
                popt,pcov  = curve_fit(fit_pulse, b[index:],y[index:], bounds = ([min_guess, 0, 0, -1],[max_guess, 100, 100, 1]))
                y_fit = fit_pulse(x_bias, popt[0], popt[1], popt[2], popt[3])

                if len(y_fit) > 1:
                    breakdown = x_bias[np.argmax(y_fit)]
                    return [breakdown*100, x_bias, y_fit]

                else:
                    return [0, 0, 0]

            except:
                    return [0, 0, 0]
        else:
            return [0, 0, 0]
    else:
        return [0, 0, 0]

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
                   
                   #channel on information
                   if len(files[j]) == 21:
                       ch = int(files[j][15])
                   else:
                       ch = int(files[j][15:17])

                   print(folders[i], files[j])
                   root_file = op(files[j])
                   current_array = root_file["tree/IV/current"].array()
                   bias = root_file["tree/IV/bias"].array()
                   # Here we need to create the first warning depending on the data quality
                   if len(bias) < 20:
                       print(f" The data {folders[i]} {files[j]} has only {len(bias)} samples. It is required at least 20 samples! ")
                       break
                    
                   n = int(len(current_array)/15)
                   current = savgol_filter(current, n, 1)

                   bkd_pulse = float(IV_PulseShape(bias,current, 1.5*n)[0])
                   #bkd_poly = ADD THE OTHER FITTING 
                   

                   if bkd_pulse != 0 and bkd_poly != 0:
                       bkd = (bkd_pulse + bkd_poly)/2 # We can change it depending on the performance comparison
                       message = f" {folders[i]} {files[j]}: Breakdown = {bkd}."
                   elif bkd_pulse == 0 and bkd_poly != 0:
                       bkd = bkd_poly
                       message = f" {folders[i]} {files[j]}: Breakdown = {bkd} (WARNING: the pulse shape fitting method failled, please check the plots)."
                   elif bkd_pulse != 0 and bkd_poly == 0:
                       bkd = bkd_pulse
                       message = f" {folders[i]} {files[j]}: Breakdown = {bkd} (WARNING: the polynomial fitting method failled, please check the plots)."
                   else:
                       message = f" {folders[i]} {files[j]}: FAILED!!!"

                   apa = ch//8
                   # I think we need to change it
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
	
	
