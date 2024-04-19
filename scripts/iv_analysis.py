'''
IV analysis 
Input: --dir folder_path related to a given run 
Output:
    - IVplots.pdf with all acquired TRIM IV curves
    - output.txt with information about the Vbd determination 
    - dic.json with information about the operating voltage of each channel

Remember to specify the current version of the program you are using! (for this program, version = 2)
'''

import click, json
import numpy as np
from os import chdir, listdir
from uproot import open as op
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter
import matplotlib
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import warnings

warnings.filterwarnings("ignore", category=matplotlib.MatplotlibDeprecationWarning)
#warnings.filterwarnings("ignore", category=OptimizeWarning)

map = {
    '10.73.137.104': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7], 'hpk': [8, 9, 10, 11, 12, 13, 14, 15]},
    '10.73.137.105': {'apa': 1, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 13, 15], 'hpk': [17, 19, 20, 22]},
    '10.73.137.107': {'apa': 1, 'fbk': [0, 2, 5, 7], 'hpk': [8, 10, 13, 15]},
    '10.73.137.109': {'apa': 2, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15], 'hpk': [16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]},
    '10.73.137.111': {'apa': 3, 'fbk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23], 'hpk': [24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]},
    '10.73.137.112': {'apa': 4, 'fbk': [], 'hpk': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 34, 37, 39]},
    '10.73.137.113': {'apa': 4, 'fbk': [0, 2, 5, 7], 'hpk': []},
}

def derivative(y):
    return np.nan_to_num(np.gradient(y)/y) 
    
def linear_function(x, m, b):
    return m * x + b

def parabolic_function(x,a,b,c):
    return a*x*x + b*x + c


def data_quality(data):
    '''
    Check the quality of the data set. Errors are returned if the sample:
        - is smaller than 20,
        - all the current values are NaN
        - more than 10 NaN values are present
        - all the current values are negative
        - all the current values are below 50
        - the first current point is larger than 30 or the last current is lower than 100

        It returns an array:
        - The first element is OK if we can continue with the analysis or BAD if we have to stop
        - The second element is a message regarding the Error / Warning associated to the data acquired
    '''
    
    if len(data) < 20:
        return 'BAD(less than 20 samples)'
    if np.count_nonzero(np.isnan(data)) == len(data):
        return 'BAD(all currents are NaN)'
    elif (np.count_nonzero(np.isnan(data)) >= 10):
        return 'BAD(more than 10 NaN for current)'
    elif (np.count_nonzero(np.isnan(data)) > 0) and (np.count_nonzero(np.isnan(data)) < 10):
        return 'Good(Warning: some NaN value for current)' 

    # No more checks on negative currents
    #if (data < 0).sum() > len(data)/2:
        #return 'BAD(negative current)' 
    #if (data < 50).sum() == len(data):
        #return 'BAD(too low current)'
    #if (data[0] > 20) or (data[len(data)-1] < 90) :
        #return 'BAD(wrong current range)'

    return 'Good'


def IV_Polynomial(x, der, step, sgf):
    '''
    2nd degree polynomial fit of the trim IV curve
    It returns an array of three element:
    -  Vbd trim from IV curve fit 
    -  Error on Vbd trim (fit error)
    -  An array with trim and filtered derivative used for the fit
    -  An array with x and y  coordinante to reconstruct the fitting function 
    -  An array with information of the savgol filter (window and degree)
    '''
    
    #Savgol filter on 1st normalized derivative
    y = savgol_filter(der, sgf[0], sgf[1])
    if np.count_nonzero(np.isnan(y)) == len(y):
        return [np.nan, np.nan, [0, 0], [0,0], sgf]

    #Search for the maximum of first filtered derivative
    peak_index = np.argmax(y)

    #Select few points around the peak (more than 5 is ok)
    if (step > 40):
        half_point_range = 6
    elif (step <= 40) and (step > 10):
        half_point_range = 8
    else:
        half_point_range = 10

    min_index = peak_index - half_point_range
    if min_index < 0:
        min_index = 0
    max_index = peak_index + half_point_range
    if max_index > len(x)-1:
        max_index = len(x)-1

    #Parabolic fit
    #poly2_coeff = np.polyfit(x[min_index:max_index], y[min_index:max_index], 2)
    poly2_coeff, poly2_cov = curve_fit(parabolic_function, np.array(x[min_index:max_index]), np.array(y[min_index:max_index]))
    poly2_errors = np.sqrt(np.diag(poly2_cov))
    
    x_poly2 = np.linspace(x[min_index], x[max_index], 100)
    y_poly2 = np.polyval(poly2_coeff, x_poly2)

    if (poly2_coeff[0] > 0): #Check if it has the correct concavity 
        return [np.nan, np.nan, [0,0], [0,0], sgf]
    else:
        #Vbd = x_poly2[np.argmax(y_poly2)]
        Vbd = -poly2_coeff[1] / (2*poly2_coeff[0])
        if (Vbd < x[5]) or (Vbd > x[len(x)-5]): #Check if Vbd is not on the first or last points 
            return [np.nan, np.nan, [0,0], [0,0], sgf]
        else:
            Vbd_error = np.sqrt((poly2_errors[1]/(2*poly2_coeff[0]))**2 + (poly2_coeff[1]*poly2_errors[0]/(2*poly2_coeff[0]*poly2_coeff[0]))**2)
            '''if Vbd_error < 1: # Plane fit
                return [np.nan, np.nan, [0,0], [0,0], sgf]
            elif Vbd_error < step:
                Vbd_error = step    
            '''
            return [Vbd, Vbd_error, [x, y], [x_poly2, y_poly2], sgf]
        


def fit_pulse(t, t0, T, A, P):
    x = (np.array(t) - t0+T)/T
    return P+A*np.power(x, 3)*np.exp(3*(1-x))


def IV_PulseShape(trim, der, step, sgf):
    '''
    Pulse Shape fit of the trim IV curve
    It returns an array of three element:
    -  Vbd trim from IV curve fit 
    -  An array with trim and filtered derivative used for the fit
    -  An array with x and y  coordinante to reconstruct the fitting function 
    -  An array with information of the savgol filter (window and degree)
    '''

    #Savgol filter on 1st normalized derivative
    x = trim/100
    y = savgol_filter(der, sgf[0], sgf[1])

    #Search for the peak
    n_cut = 10 # Vbd seems to be always after the second half of the plot
    peak = savgol_filter(y, 20, 2)[n_cut:]
    index = (np.argmax(peak) + n_cut) - 3 # 3is an arbitrary constant that can be changed according with the amount of data
    
    #Choosing boundaries values for the fitting
    delta = len(x) - index
    if delta >= 5 and index >= 5:
        min_guess = x[index-5]
        max_guess = x[len(x)-1]
    if delta < 5 and index >= 5:
        min_guess = x[index - int(delta/2)]
        max_guess = x[index + int(delta/2)]
    if index <= 5:
        min_guess = x[0]
        max_guess = x[index + 5]

    #Fit using a pulse shape function
    x_pulse = np.arange(min_guess, x[len(x)-1], 0.01)
    try:
        popt, pcov = curve_fit(fit_pulse, x[index:], y[index:], bounds=([min_guess, 0, 0, -0.5], [max_guess, 100, 100, 0.5]))
        y_pulse = fit_pulse(x_pulse, popt[0], popt[1], popt[2], popt[3])

        if (len(y_pulse) < 2) or (y_pulse[0]==y_pulse.max()) or (y_pulse[-1]==y_pulse.max()) or (np.max(y_pulse) > 5*np.max(y[index:])):
            return [np.nan, np.nan, [0, 0], [0, 0], sgf]
        else:
            #Vbd = x_pulse[np.argmax(y_pulse)] *100
            Vbd = popt[0]*100
            Vbd_error = (np.sqrt(np.diag(pcov))[0])*100
            if Vbd_error < step:
                Vbd_error = step
            if (Vbd > 100) and (Vbd < x.max()*100-100):
                return [Vbd, Vbd_error, [x*100, y], [x_pulse*100, y_pulse], sgf]
            else:
                return [np.nan, np.nan, [0, 0], [0, 0], sgf]
    except:
        return [np.nan, np.nan, [0, 0], [0, 0], sgf]


def plot_trim(data_status, trim, current, c_filtered, Polynomial, PulseShape):
    '''  To create the plot of the Trim IV curve, with fit results (if fit works) '''
    fig, ax = plt.subplots(figsize=(8,6))
    ax.set_xlabel("Trim (DAC)")
    ax.set_ylabel("Current") #Unit of measure(?)
    #ax.set_yscale('log')
    ax.scatter(trim, current, marker='o',s=5, color='blue', label='Acquired Trim IV curve')
    if data_status == 'Good':
        #ax.scatter(trim, c_filtered[0], marker='o',s=5, color='deepskyblue', label=f'Filtered IV curve SGF(w={c_filtered[1]:.0f}, d={c_filtered[2]:.0f})')
    
        ax_twin = ax.twinx()
        ax_twin.set_ylabel('Normalized Derivative')
        ax_twin.scatter(trim,derivative(current), marker='o', s=5, color='orange', label='Derivative of filtered data') 
        ax_twin.set_ylim([min(derivative(current))*0.3, max(derivative(current))*2])

        if not np.isnan(Polynomial[0]): # Polynomial fit
            ax_twin.scatter(Polynomial[2][0],Polynomial[2][1], marker='o', s=5, color='mediumseagreen', label=f'Filtered derivative for Polyfit SGF(w={Polynomial[4][0]:.0f}, d={Polynomial[4][1]:.0f})')
            ax_twin.plot(Polynomial[3][0],Polynomial[3][1],color='green', label = '2nd polyfit')
            ax_twin.axvline(x=Polynomial[0], color='lime' ,linestyle='--', label= r'Poly trim $V_{bd}$* = '+f'{Polynomial[0]:.0f} +/- {Polynomial[1]:.0f} (DAC)')
            ax_twin.set_ylim([min(Polynomial[2][1])*0.3, max(Polynomial[2][1])*2])

        if not np.isnan(PulseShape[0]): # Pulse shape fit 
            ax_twin.scatter(PulseShape[2][0], PulseShape[2][1], marker='o', s=5, color='violet', label=f'Filtered derivative for Pulse fit SGF(w={PulseShape[4][0]:.0f}, d={PulseShape[4][1]:.0f})')
            ax_twin.plot(PulseShape[3][0], PulseShape[3][1],color='purple', label = 'Pulse fit')
            ax_twin.axvline(x=PulseShape[0], color='fuchsia' ,linestyle='--', label= r'Pulse trim $V_{bd}$* = '+f'{PulseShape[0]:.0f} +/- {PulseShape[1]:.0f} (DAC)')
    
        ax_twin.legend(loc='upper left',fontsize='7')
        
    ax.legend(loc='center left',fontsize='7')
    return fig


def plot_bias(bias, current, Vbd_bias):
    '''  To create the plot of the Bias IV curve  '''
    fig, ax = plt.subplots(figsize=(8,6))
    ax.set_xlabel("Bias (DAC)")
    ax.set_ylabel("Current") #Unit of measure(?)
    #ax.set_yscale('log')
    ax.scatter(bias, current, marker='o',s=5, color='blue', label='Acquired Bias IV curve')
    ax.axvline(x=Vbd_bias, color='red' ,linestyle='--', label= r'Bias $V_{bd}$* = '+f'{Vbd_bias:.0f} (DAC)')
    ax.legend(loc='center left',fontsize='7')
    return fig
    

def plot_bias_trim(bias, current_bias, bias_conversion, trim, current_trim):
    '''
    To create the plot of the whole IV curve (trim and bias) in terms of volts
    '''
    bias_v = bias_conversion[0]*np.array(bias) + bias_conversion[1] 
    trim_v = bias_v[-1] - np.array(trim) * (4.4/4095.0)
    fig, ax = plt.subplots(figsize=(8,6))
    ax.set_xlabel("Volt")
    ax.set_ylabel("Current") #Unit of measure(?)
    #ax.set_yscale('log')
    ax.scatter(bias_v, current_bias, marker='o',s=5, color='blue', label='Acquired Bias IV curve')
    ax.scatter(trim_v, current_trim, marker='o',s=5, color='red', label='Acquired Trim IV curve')
    ax.legend(loc='center left',fontsize='7')
    return fig

def plot_IVbias_AFE(bias_list, current_list, Vbd_list, channels):
    '''   To create the plot of Bias IV curve for each AFE '''
    fig, ax = plt.subplots(figsize=(8,6))
    ax.set_xlabel("Bias (DAC)")
    ax.set_ylabel("Current") #Unit of measure(?)
    #ax.set_yscale('log')
    color_list = ['red','blue','green','purple','orange','grey','aqua','violet']
    for i in range(len(bias_list)):
        ax.scatter(bias_list[i], current_list[i], marker='o',s=5, color=color_list[i], label=f'Channel: {channels[i]:.0f}')
        #ax.plot(bias_list[i], current_list[i], color=color_list[i], label=f'Channel: {channels[i]:.0f}')
        #ax.axvline(x=Vbd_list[i], color=color_list[i] ,linestyle='--', label= r'Bias $V_{bd}$ = '+f'{Vbd_list[i]:.0f} (DAC)')
    ax.legend(loc='center left',fontsize='7')
    return fig
    

def DAC_VOLT_bias_conversion(bias_dac, bias_conversion):
    '''  Bias conversion: from DAC to VOLT '''
    if np.isnan(bias_dac):
        return np.nan
    else:
        return bias_conversion[0]*bias_dac + bias_conversion[1]

def DAC_VOLT_trim_conversion(trim_dac):
    '''  Trim conversion: from DAC to VOLT '''
    if np.isnan(trim_dac):
        return np.nan
    else:
        return trim_dac * (4.4/4095.0)

def DAC_VOLT_full_conversion (bias_dac, trim_dac, bias_conversion):
    '''  To obtain VOLTS from TRIM and BIAS in DAC'''
    if np.isnan(bias_dac) or np.isnan(trim_dac):
        return np.nan
    else:
        return DAC_VOLT_bias_conversion(bias_dac,bias_conversion) - DAC_VOLT_trim_conversion(trim_dac)

def VOLT_DAC_full_conversion (V_volt, bias_conversion):
    ''' From VOLTS, to DAC BIAS and TRIM to set (integer counts) '''
    bias_dac = int( (V_volt - bias_conversion[1])/bias_conversion[0]) + 2 #Integer number of DAC counts for BIAS
    bias_V = DAC_VOLT_bias_conversion(bias_dac,bias_conversion)
    trim_dac = int ((bias_V - V_volt) / (4.4/4095.0)) #Integer number of DAC counts for TRIM
    trim_V = DAC_VOLT_trim_conversion(trim_dac)
    V_volt_set = bias_V - trim_V
    if (trim_dac < 0) or (trim_dac > 4090) or (abs(V_volt_set-V_volt)>0.1):
        print('VOLT - DAC Error conversion')
        return np.nan,np.nan,np.nan
    else:
        return bias_dac, trim_dac, V_volt_set


######################################################################################

@click.command()
@click.option("--dir", default='/eos/experiment/neutplatform/protodune/experiments/ProtoDUNE-II/PDS_Commissioning/ivcurves/Mar-21-2024-run00')
def main(dir):
    version = 2 # SPECIFY THE SCRIPT VERSION
    chdir(dir)
    ENDPOINT_FOLDERS = sorted(listdir()) #List of folders in the input directory, each one is realetd to an endpoint
    for endpoint_folder in ENDPOINT_FOLDERS: #Cycle on endpoint_folders in the input directory
        if len(endpoint_folder) > 40:
            timestamp = f"{(endpoint_folder.split('/')[-1]).split('_')[0]}_{(endpoint_folder.split('/')[-1]).split('_')[1]}" #Ex run
            ip_address = (endpoint_folder.split('/')[-1]).split('ip')[-1]
            endpoint = ip_address[-3:]
            apa = int((endpoint_folder.split('/')[-1].split('apa')[-1]).split('_')[0])

            dic = map[ip_address]

            # To save information of each channel, divided by AFE
            DAC_V_bias_AFE = [[[],[]], [[],[]], [[],[]], [[],[]], [[],[]]] 
            sipm_AFE = [[], [], [], [], []]
            channel_AFE = [[], [], [], [], []]
            Vbd_bias_dac_AFE = [[], [], [], [], []]
            Vbd_trim_dac_AFE = [[], [], [], [], []]
            Vbd_V_AFE = [[], [], [], [], []] 
            bias_dac_AFE = [[], [], [], [], []]
            current_bias_AFE = [[], [], [], [], []]

            pdf_file = PdfPages(f'{dir}/{str(endpoint_folder)}/{ip_address}_Trim_IVplots_v{version:.0f}.pdf')
            pdf_file_bias = PdfPages(f'{dir}/{str(endpoint_folder)}/{ip_address}_Bias_IVplots_v{version:.0f}.pdf')
            pdf_file_bias_trim = PdfPages(f'{dir}/{str(endpoint_folder)}/{ip_address}_IVplots_v{version:.0f}.pdf')
            text_file = open(f'{dir}/{str(endpoint_folder)}/{ip_address}_output_v{version:.0f}.txt', 'w')

            text_file.write(f'IP\tFile_name\tTimestamp\tSIPM_type\tTrim_data_quality\tMin_I\tMax_I\tFit_status\tPoly_Vbd_trim(DAC)\tPoly_Vbd_trim_error(DAC)\tPulse_Vbd_trim(DAC)\tPulse_Vbd_trim_error(DAC)\tVbd_bias(DAC)\tVbd_bias(V)\tVbd_bias_error(V)\tBias_conversion_slope\tBias_conversion_intercept\tVbd(V)\n')
            
            #text_file.write(f'IP\tFile_name\tTimestamp\tSIPM_type\tTrim_data_quality\tMin_I\tMax_I\tFit_status\tPoly_Vbd_trim(DAC)\tPulse_Vbd_trim(DAC)\tMean_Vbd_trim(DAC)\tError_Vbd_trim(DAC)\tVbd_bias(DAC)\tBias_conversion_slope\tBias_conversion_intercept\tVbd(V)\tError_Vbd(V)\n')
            
            chdir(f"{dir}/{str(endpoint_folder)}")
            FILES = [] #List of files in the endpoint_folder selected

            print(f'\n\n ---------------------------------------------------------------  \n\nENDPOINT: {ip_address} \t {timestamp} \n\n')
            if ('mar' in timestamp.lower()) and ('2024' in timestamp)and (int(timestamp.split('-')[1]) <19):
                print('Wrong data format, before 19th March 2024')
                continue
            else:
                #Good data format - after 19th March 2024
                for file in listdir(): #Cycle on root file in the selected endpoint folder
                    if file[len(file)-4:] == 'root':
                        FILES.append(file)

                print('-- BIAS scan and Trim IV CURVE analysis --\n')
                for ch in dic['fbk']+dic['hpk']:
                    file_name = 'apa_' + str(apa) + '_afe_' + str(ch//8) + '_ch_' + str(ch) + '.root' #root filename we should have
                    afe = int(ch//8)
                    if ch in dic['fbk']:
                        sipm = 'FBK'
                        Vbd_roomT = 32.5
                        Vbd_ln2T = 26.9
                    else:
                        sipm = 'HPK'
                        Vbd_roomT = 51
                        Vbd_ln2T = 41.5
                        
                    if file_name in FILES: #Check if the file is present 
                        root_file = op(file_name)
    
                        #Vbd BIAS determination + conversion (from DAC to VOLT)
                        bias_dac = root_file["tree/bias/bias_dac"].array()
                        bias_V = root_file["tree/bias/bias_v"].array()
                        bias_c = root_file["tree/bias/current"].array() *(-1) # Attention: available only for new data (from ????)
                        #DAC_V_bias_conversion= np.polyfit(bias_dac, bias_V, 1)
                        DAC_V_bias_conversion, covariance = curve_fit(linear_function, np.array(bias_dac), np.array(bias_V))
                        DAC_V_bias_conversion_errors = np.sqrt(np.diag(covariance))
                        #print(f'Bias slope:{DAC_V_bias_conversion[0]:.5f} +/- {DAC_V_bias_conversion_errors[0]:.5f}')
                        #print(f'Bias intercept:{DAC_V_bias_conversion[1]:.3f} +/- {DAC_V_bias_conversion_errors[1]:.3f}')

                        Vbd_bias_dac = int(bias_dac[len(bias_dac)-1])
                        Vbd_bias_V = DAC_V_bias_conversion[0]*Vbd_bias_dac + DAC_V_bias_conversion[1]
                        Vbd_bias_V_error = np.sqrt((Vbd_bias_V*DAC_V_bias_conversion_errors[0])**2+(DAC_V_bias_conversion_errors[1])**2)

                        fig_bias = plot_bias(bias_dac, bias_c, Vbd_bias_dac)
                        fig_bias.suptitle(f'REV Bias IV curve \n ENDPOINT:{endpoint} APA:{apa:.0f} AFE:{afe:.0f} CH:{ch:.0f} SiPM:{sipm}')
                        plt.tight_layout()
                        pdf_file_bias.savefig(fig_bias)
                        plt.close(fig_bias)

                        bias_dac_AFE[afe].append(bias_dac) 
                        current_bias_AFE[afe].append(bias_c)
                        
                        #Vbd TRIM determination (iv curves)
                        current = (root_file["tree/iv_trim/current"].array()) *(-1) #Attention: current flip to take into accoubt at the end!
                        trim = root_file["tree/iv_trim/trim"].array()
                        start_time = root_file["tree/run/time_start"].array()[0]
                        end_time = root_file["tree/run/time_end"].array()[0]


                        fig_bias_trim = plot_bias_trim(bias_dac, bias_c, DAC_V_bias_conversion, trim,  current)
                        fig_bias_trim.suptitle(f'REV IV curve \n ENDPOINT:{endpoint} APA:{apa:.0f} AFE:{afe:.0f} CH:{ch:.0f} SiPM:{sipm}')
                        plt.tight_layout()
                        pdf_file_bias_trim.savefig(fig_bias_trim)
                        plt.close(fig_bias_trim)

                        current = (root_file["tree/iv_trim/current"].array())[::-1]  *(-1)
                        
                        #Check data quality 
                        data_status = data_quality(np.array(current))
    
                        if data_status == 'Good':
                            # No more checks on negative currents
                            '''
                            # Select data for fit: only positive current
                            t = [] #Trim for fit
                            c = [] #Current for fit
                            print(current)
                            print(len(current))
                            for k in range(len(current)):
                                if current[k] > 0:
                                    c.append(current[k])
                                    t.append(trim[k])
                            c = np.array(c)
                            t = np.array(t)
                            '''

                            c = np.array(current)
                            t = np.array(trim)
    
                            # First Savitzky–Golay filter on IV curve, with a variable window
                            step = np.diff(t)[0]
                            if (step > 45):
                                sgf_IV_window = 5
                            elif (step <= 45) and (step > 10):
                                sgf_IV_window = 6
                            else:
                                sgf_IV_window = 8
    
                            if (int(endpoint)==107): #Exception for endpoint 107 - it seems noisy (To be checked...)
                                sgf_IV_window = 10
                                
                            sgf_IV_degree = 1
                            c_filtered = [savgol_filter(c, sgf_IV_window, sgf_IV_degree), sgf_IV_window, sgf_IV_degree] #Filtered current with information on the filter
                            der_c =  derivative(c_filtered[0]) #First normalized derivative of filtered current
    
                            #Polynomial Fit
                            sgf_poly = [3*sgf_IV_window, 2]
                            Polynomial = IV_Polynomial(t, der_c, step, sgf_poly)
                            while ((float(Polynomial[0]) == 0) and (sgf_poly[0]<31)):
                                sgf_poly[0] += 2
                                Polynomial = IV_Polynomial(t, der_c, step, sgf_poly)
                              
                            #Pulse shape Fit
                            sgf_pulse = [2, 1]
                            PulseShape = IV_PulseShape(t, der_c, step, sgf_pulse)
                            while ((float(PulseShape[0]) == 0) and (sgf_pulse[0]<10)):
                                sgf_pulse[0] += 2
                                PulseShape = IV_PulseShape(t, der_c, step, sgf_pulse)  
                                                    
                        else: #If the file is not present
                            c_filtered = [0, 0, 0]
                            Polynomial = [np.nan,np.nan,[0,0],[0,0],[0,0]]
                            PulseShape = [np.nan,np.nan, [0,0],[0,0],[0,0]]
    
                        #Plot for each IV trim curve (with fits if they works)
                        fig = plot_trim(data_status, trim, current, c_filtered, Polynomial, PulseShape)
                        fig.suptitle(f'REV Trim IV curve \n ENDPOINT:{endpoint} APA:{apa:.0f} AFE:{afe:.0f} CH:{ch:.0f} SiPM:{sipm}')
                        plt.tight_layout()
                        pdf_file.savefig(fig)
                        plt.close(fig)

                        #Check the results for Vbd trim (DAC)
                        # Vbd_trim_dac is the best estimation for the trim -> How do we evaluate it?
                        Vbd_trim_dac_poly = Vbd_trim_dac_pulse = np.nan
                        if (not np.isnan(Polynomial[0])) and (not np.isnan(PulseShape[0])):
                            Vbd_trim_dac_poly = max(trim)-float(Polynomial[0])
                            Vbd_trim_dac_pulse = max(trim)-float(PulseShape[0]) 
                            Delta = Vbd_trim_dac_pulse - Vbd_trim_dac_poly
                            if abs(Delta) < 200 : 
                                #If both method works and the results are quite similar, Vbd_trim_dac = mean value
                                Vbd_trim_dac = round(int((Vbd_trim_dac_pulse + Vbd_trim_dac_poly)/2))
                                Vbd_trim_dac_error = abs(Delta)/2 #To be estimated...
                                fit_status = "Good"
                            else:
                                # If both method works but the results are very different, you have to check the data manually 
                                Vbd_trim_dac = round(int((Vbd_trim_dac_pulse + Vbd_trim_dac_poly)/2)) #Check
                                Vbd_trim_dac_error = np.nan #To be estimated
                                fit_status = f'Check(Delta={Delta:.0f})'
                        elif (not np.isnan(Polynomial[0])) and (np.isnan(PulseShape[0])):
                             # If only the the Poly method works, we take Vbd_trim_dac 
                            Vbd_trim_dac = Vbd_trim_dac_poly = max(trim)-float(Polynomial[0])
                            Vbd_trim_dac_error = 0 #To be estimated
                            fit_status = "Pulse_fit_failed"
                        elif (not np.isnan(PulseShape[0])) and (np.isnan(Polynomial[0])):
                            # If only the the Pulse method works, we take Vbd_trim_dac  
                            Vbd_trim_dac = Vbd_trim_dac_pulse = max(trim)-float(PulseShape[0])
                            Vbd_trim_dac_error = 0 #To be estimated
                            fit_status = "Poly_fit_failed"
                        else:
                            #If both methods doesn't work, we have no result
                            Vbd_trim_dac = np.nan
                            Vbd_trim_dac_error = np.nan
                            fit_status = "Fits_failed"

                        Vbd_trim_dac_poly_error = Polynomial[1]
                        Vbd_trim_dac_pulse_error = PulseShape[1]
                        
                        #DAC - VOLT convesion to estimate the breakdown voltage (V)
                        Vbd_V = DAC_VOLT_full_conversion(Vbd_bias_dac, Vbd_trim_dac, DAC_V_bias_conversion)
                        Vbd_V_error = 0 # To be defined....
                        
                         #text_file.write(f'{ip_address}r\t{file_name}\t{timestamp}\t{sipm}\t{data_status}\t{min(current):.2f}\t{max(current):.2f}\t{fit_status}\t{Vbd_trim_dac_poly:.0f}\t{Vbd_trim_dac_pulse:.0f}\t{Vbd_trim_dac:.0f}\t{Vbd_trim_dac_error:.0f}\t{Vbd_bias_dac}\t{DAC_V_bias_conversion[0]:.5f}\t{DAC_V_bias_conversion[1]:.3f}\t{Vbd_V:.2f}\t{Vbd_V_error:.2f}\n')

                        #Save information in the output txt file
                        text_file.write(f'{ip_address}\t{file_name}\t{timestamp}\t{sipm}\t{data_status}\t{min(current):.2f}\t{max(current):.2f}\t{fit_status}\t{Vbd_trim_dac_poly:.0f}\t{Vbd_trim_dac_poly_error:.0f}\t{Vbd_trim_dac_pulse:.0f}\t{Vbd_trim_dac_pulse_error:.0f}\t{Vbd_bias_dac}\t{Vbd_bias_V:.3f}\t{Vbd_bias_V_error:.3f}\t{DAC_V_bias_conversion[0]:.5f}\t{DAC_V_bias_conversion[1]:.3f}\t{Vbd_V:.3f}\n')
                    
                        
                        #Save information per AFE
                        DAC_V_bias_AFE[afe][0].append(DAC_V_bias_conversion[0])
                        DAC_V_bias_AFE[afe][1].append(DAC_V_bias_conversion[1])
                        sipm_AFE[afe].append(sipm)
                        channel_AFE[afe].append(ch)
                        Vbd_V_AFE[afe].append(Vbd_V)
                        Vbd_bias_dac_AFE[afe].append(Vbd_bias_dac)
                        Vbd_trim_dac_AFE[afe].append(Vbd_trim_dac)

                        '''
                        if (Vbd_V < Vbd_roomT) and (Vbd_V > Vbd_ln2T):
                            print(f'\n\n\n ----- IP: {ip_address} Time: {timestamp} Channel: {ch:.0f} \t Vbd : {Vbd_V:.3f} V \n\n\n')
                        #print(f'Vbd : {Vbd_V:.3f} V')
                        '''
                        
                        #Print information 
                        print(f'Channel: {ch:.0f}')
                        print(f'Vbd_bias: {Vbd_bias_dac:.0f} DAC --> {Vbd_bias_V:.3f} +/- {Vbd_bias_V_error:.3f} V')
                        print(f'Data_status: {data_status}')
                        print(f'Fit_status: {fit_status}')
                        print(f'Poly: {Polynomial[0]:.0f} +/- {Polynomial[1]:.0f} DAC')
                        print(f'Pulse: {PulseShape[0]:.0f} +/- {PulseShape[1]:.0f} DAC')
                        print(f'Vbd : {Vbd_V:.3f} V')
                        print()
                        
    
                        del Polynomial, PulseShape, Vbd_trim_dac_poly, Vbd_trim_dac_pulse, Vbd_V
    
                    else:
                        print(f'Missing file: {file_name}\n')

                        text_file.write(f'{ip_address}\t{file_name}\t{timestamp}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}t{np.nan}\n')
                        #text_file.write(f'{ip_address}\t{file_name}\t{timestamp}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\t{np.nan}\n')
    
                        DAC_V_bias_AFE[afe][0].append(np.nan)
                        DAC_V_bias_AFE[afe][1].append(np.nan)
                        sipm_AFE[afe].append(sipm)
                        channel_AFE[afe].append(ch)
                        Vbd_V_AFE[afe].append(np.nan)
                        Vbd_bias_dac_AFE[afe].append(np.nan)
                        Vbd_trim_dac_AFE[afe].append(np.nan)
                        bias_dac_AFE[afe].append([]) 
                        current_bias_AFE[afe].append([])
                
                pdf_file.close()
                pdf_file_bias.close()
                pdf_file_bias_trim.close()
                text_file.close()


                pdf_file_bias_AFE = PdfPages(f'{dir}/{str(endpoint_folder)}/{ip_address}_Bias_IVplots_AFE_v{version:.0f}.pdf')
                for afe in range(5):
                    if len(channel_AFE[afe]) != 0:
                        fig_AFE = plot_IVbias_AFE(bias_dac_AFE[afe], current_bias_AFE[afe], Vbd_bias_dac_AFE[afe], channel_AFE[afe])
                        fig_AFE.suptitle(f'REV Bias IV curve \n ENDPOINT:{endpoint} APA:{apa:.0f} SiPM:{sipm_AFE[afe][0]} AFE:{afe:.0f}')
                        plt.tight_layout()
                        pdf_file_bias_AFE.savefig(fig_AFE)
                        plt.close(fig_AFE)
                
                pdf_file_bias_AFE.close()
                
                '''
                #To determine the BIAS and TRIM (in terms of DAC) to set, taking into account Overvoltage 
                FBK_op_bias_dac = [] 
                FBK_op_trim_dac = []
                HPK_op_bias_dac = [] 
                HPK_op_trim_dac = []

                print('\n\n -- Determination of SiPM operating voltage --')
    
                for AFE in range(5):
                    print(f'\n\n------------- \nAFE: {AFE:.0f}\n')
                    op_trim_dac_list= []
                    
                    if len(channel_AFE[AFE]) == 0: #If the afe is not used, continue
                        print('Not used')
                        continue
                        
                    elif all(np.isnan(x) for x in Vbd_bias_dac_AFE[AFE]) or (all(np.isnan(x) for x in Vbd_trim_dac_AFE[AFE])) or (all(np.isnan(x) for x in Vbd_V_AFE[AFE])): #If all data about an afe are not good, returns nan
                        print('Only NaN data')
                        op_bias_dac = np.nan
                        op_trim_dac_list = np.full(len(channel_AFE[AFE]), np.nan).tolist()
                       
                    else:
                        if sipm_AFE[AFE][0] == 'FBK':
                            ov_V = 4.5
                        else:
                            ov_V = 3
                            
                        mean_DAC_V_bias = [np.nanmean(DAC_V_bias_AFE[AFE][0]),np.nanmean(DAC_V_bias_AFE[AFE][1])] #Mean conversion coefficients
                        VOP_max = np.nanmax(Vbd_V_AFE[AFE])  + ov_V #Maximum operating voltage
                        op_bias_dac = VOLT_DAC_full_conversion(VOP_max, mean_DAC_V_bias)[0] #Maximum bias value -> BIAS DAC to set
                        op_bias_v = DAC_VOLT_bias_conversion(op_bias_dac,mean_DAC_V_bias)
                        print(f'Fixed bias: {op_bias_dac:.0f} DAC --> {op_bias_v:.3f} V\n')
    
                        for i in range(len(channel_AFE[AFE])):
                            if np.isnan(Vbd_V_AFE[AFE][i]):
                                V_op = np.nan
                                op_trim_dac = np.nan
                            else:
                                V_op = Vbd_V_AFE[AFE][i] + ov_V #Operating voltage
                                op_trim_dac = int( (op_bias_v - V_op) / (4.4/4095.0) ) #Trim DAC to set

                            
                            print(f'Channel: {channel_AFE[AFE][i]:.0f}')
                            print(f'Vop to set (Vbd+Vov): {V_op:.3f} V --> Voltage applied: {DAC_VOLT_full_conversion(op_bias_dac,op_trim_dac,mean_DAC_V_bias):.3f} V')
                            print(f'Bias: {op_bias_dac:.0f} DAC --> {op_bias_v:.3f} V')
                            print(f'Trim: {op_trim_dac:.0f} DAC --> {DAC_VOLT_trim_conversion(op_trim_dac):.3f} V\n')
                            op_trim_dac_list.append(op_trim_dac)
                            
    
                    if sipm_AFE[AFE][0] == 'FBK':
                        FBK_op_bias_dac += [op_bias_dac] 
                        FBK_op_trim_dac += op_trim_dac_list
                    else:
                        HPK_op_bias_dac += [op_bias_dac] 
                        HPK_op_trim_dac += op_trim_dac_list
    
    
                # JSON FILE
                # Since JSON file doesn't support NaN, i convert it to None
                dic['FBK_op_bias'] = [x if not np.isnan(x) else None for x in FBK_op_bias_dac]
                dic['FBK_op_trim'] = [x if not np.isnan(x) else None for x in FBK_op_trim_dac]
                dic['HPK_op_bias'] = [x if not np.isnan(x) else None for x in HPK_op_bias_dac]
                dic['HPK_op_trim'] = [x if not np.isnan(x) else None for x in HPK_op_trim_dac]
                dic['timestamp'] = timestamp
                
                with open(f'{dir}/{str(endpoint_folder)}/{ip_address}_dic.json', "w") as fp:
                    json.dump(dic, fp) # Vbd=None means some error!!
                    
                '''

######################################################################################

if __name__ == "__main__":
    main()

