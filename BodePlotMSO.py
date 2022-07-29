#########################################################################
# Script to generate bode plot on 2 Series MSO (1.42.0.219)             #
# CH2 of scope should connect to AFG Out scope                          #
# CH1 of scope should connect to output of DUT                          #
# AFG Out of scope should connect to input of DUT                       #
# Add 50 Ohm feed through to channel 1 for high frequency               #
# Prerequisites - PyVISA (1.12.0), numpy (1.23.0), matplotlib (3.5.2)   #
#########################################################################

import pyvisa as visa
import numpy as np
import math
import pylab as pl
import time

debug = 1

visa_address = 'USB::0x0699::0x052C::Q100002::INSTR'

rm = visa.ResourceManager()
scope = rm.open_resource(visa_address)
scope.timeout = 10000
scope.write("header OFF")
scope.write("*RST")
scope.write("*CLS")

print(scope.query("*IDN?"))
print("Connection successful")

# select test parameters
if(debug):
    start = 200000
    stop = 2000000
    steps = 100
else:
    start = int(input("Enter start frequency (Hz):"))
    stop = int(input("Enter stop frequency (Hz):"))
    steps = int(input("Enter number of steps (#):"))

freq_range = np.linspace(start, stop, steps)
amplitude = []
phase = []
loop = 0

print("Configuring scope...")

# set up scope
scope.write("DISplay:WAVEView1:VIEWStyle OVERLAY")
scope.write("SELect:CH2 1")

scope.write("CH1:sca 0.1")
scope.write("CH1:PROBEFunc:EXTAtten 1")

scope.write("CH2:sca 0.2")
scope.write("CH2:PROBEFunc:EXTAtten 1")

scope.write("acquire:mode AVErage")
scope.write("acquire:numavg 8")

scope.write("CH1:COUPling AC")
scope.write("CH2:COUPling AC")

scope.write("trig:a:edge:sou CH2")

# set up measurements
scope.write("MEASUrement:MEAS1:TYPe AMPLITUDE")
scope.write("MEASUrement:MEAS1:SOUrce CH1")
scope.write("MEASUrement:MEAS1:state on")

scope.write("MEASUrement:MEAS2:TYPe PHASE")
scope.write("MEASUrement:MEAS2:SOUrce1 CH1")
scope.write("MEASUrement:MEAS2:SOUrce2 CH2")
scope.write("MEASUrement:MEAS2:state on")

scope.write("MEASUrement:MEAS3:TYPe AMPLITUDE")
scope.write("MEASUrement:MEAS3:SOUrce CH2")
scope.write("MEASURement:MEAS3:state on")

# set up AFG
scope.write("afg:outp:loa:imped FIFTY")
scope.write("afg:func SINE")
scope.write("afg:ampl 1")
scope.write("afg:outp:state ON")
scope.query("*OPC?")

print("Beginning test...\n")

for f in freq_range:
    loop += 1

    # adjust scaling
    scope.write("afg:freq {}".format(str(f)))
    scope.query("*OPC?")
    
    scope.write("hor:sca {}".format(str(1/(f))))
    scope.write("CH1:sca {}".format(float(scope.query("MEASUrement:MEAS1:value?"))*.15))
    scope.query("*OPC?")
    
    vert_amp = float(scope.query("MEASUrement:MEAS1:value?"))

    # ensure accurate scaling
    while(int(scope.query("CH2:CLIPping?")) == 1):
        scope.write("CH2:sca {}".format(float(scope.query("MEASUrement:MEAS3:value?"))*0.5))
        scope.query("*OPC?")

    while((float(scope.query("MEASUrement:MEAS3:value?"))/((float(scope.query("ch2:sca?")))*8) < 0.5) and float(scope.query("CH2:SCAle?")) != 0.001):
        scope.write("CH2:sca {}".format(float(scope.query("MEASUrement:MEAS3:value?"))*0.15))
        scope.query("*OPC?")

    while(int(scope.query("CH1:CLIPping?")) == 1):
        scope.write("CH1:sca {}".format(vert_amp*0.5))
        vert_amp = float(scope.query("MEASUrement:MEAS1:value?"))
        scope.query("*OPC?")

    while((vert_amp/((float(scope.query("ch1:sca?")))*8) < 0.5) and float(scope.query("CH1:SCAle?")) != 0.001):
        scope.write("CH1:sca {}".format(vert_amp*.15))
        vert_amp = float(scope.query("MEASUrement:MEAS1:value?"))
        scope.query("*OPC?")
        
    scope.write("CH1:sca {}".format(vert_amp*.15))
    scope.query("*OPC?")

    # pull stable measurements
    time.sleep(0.5)
    ph = float(scope.query("MEASUrement:MEAS2:value?")) - 360
    amp_ch1 = float(scope.query("MEASUrement:MEAS1:value?"))
    amp_ch2 = float(scope.query("MEASUrement:MEAS3:value?"))
    scope.query("*OPC?")

    # error checking
    if(amp_ch1 == 9.91e37):
        amplitude.append(amplitude[-1])
    else:
        amplitude.append(20*math.log10(amp_ch1/amp_ch2))

    if(ph == 9.91e+37):
        phase.append(phase[-1])
    else:
        phase.append(ph)
        
    print("{} of {}".format(loop, steps))
    print("Frequency: {} Hz".format(f))
    print("Amplitude: {} dB".format(20*math.log10(amp_ch1/amp_ch2)))
    print("Phase: {}°\n".format(ph))

'''
# error checking
r = int(scope.query('*esr?'))
print('event status register: 0b{:08b}'.format(r))
r = scope.query('allev?').strip()
print('all event messages: {}'.format(r))
'''

# disconnect
scope.close()
rm.close()

# plot amplitude and phase
pl.figure(1)
pl.subplot(211)
pl.plot(freq_range, amplitude)
pl.xscale('log')
pl.grid(True)
pl.title("Amplitude")
pl.xlabel("Frequency (Hz)")
pl.ylabel("Amplitude (dB)")

pl.subplot(212)
pl.plot(freq_range, phase)
pl.xscale('log')
pl.grid(True)
pl.title("Phase")
pl.xlabel("Frequency (Hz)")
pl.ylabel("Phase (°)")
 

pl.tight_layout()
pl.show()
