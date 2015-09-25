#!/usr/bin/env python3

# Programm zur Ansteuerung des Störkörpermessstandes
# Konfiguration der Messung beispielsweise in "example.ini"
# Kommandozeilenargumente: python3 stoerkoerpermessung.py -h
#
# benötigt: python3 & pyserial

from argparse import ArgumentParser
from configparser import ConfigParser
import sys
import os
from serial import Serial
from motor import Motor
from vna import VNA
from time import sleep, asctime

class Stoerkoerpermessung:
    def __init__(self, config, filename):
        # Config auslesen
        self.config_filename = config
        self.config = ConfigParser()
        self.config.read(config)
        
        self.out_filename = filename
        
        self.init_motor()
        self.init_vna()
        
    def init_motor(self):
        # Abkürzung
        settings = self.config["MOTOR"]
        
        # Serial-Config
        port = settings["Port"]
        baudrate = int(settings["Baudrate"])
        serial_timeout = float(settings["SerialTimeout"])
        
        self.motor_serial = Serial(port, baudrate, timeout=serial_timeout)
        
        # Motor-Config
        motor_name = settings["Name"]
        motor_config = settings["Config"]
        
        self.motor = Motor(self.motor_serial, motor_name)
        self.motor.load_motor_config(motor_config)
        self.motor.scaling = float(settings["Scaling"])
    
    def init_vna(self):
        # Abkürzung
        settings = self.config["VNA"]
        
        # Serial-Config
        port = settings["Port"]
        baudrate = int(settings["Baudrate"])
        
        self.vna = VNA(port, baudrate)
        
        # VNA-Settings
        points = int(settings["Points"])
        power = int(settings["Power"])
        average = int(settings["Average"])
        
        self.vna.set_points(points)
        self.vna.set_power(power)
        self.vna.set_avg(average)
        
        self.vna.measurecycles()
    
    def measure(self):
        #Abkürzung
        settings = self.config["MEASUREMENT"]
        
        start = float(settings["Start"])
        stop = float(settings["Stop"])
        
        # Infinite-Modus
        infinite = settings.getboolean("Infinite")
        
        # ResonanceCurve-Modus
        rc_mode = settings.getboolean("CaptureResonanceCurve")
        rc_folder = settings["ResonanceCurveFolder"]
        
        # Checkmode Settings
        checkmode = settings.getboolean("Checkmode")
        cm_reference = float(settings["ReferencePoint"])
        
        if start > stop:
            start, stop = stop, start
        
        # Überprüfung welche Methode der Berechnung der stepsize gewählt wurde.
        # Entweder aus der Anzahl der Schritte oder mit fester angegebener step-
        # size
        if not (("StepSize" in settings) ^ ("Steps" in settings)):
            raise RuntimeError("StepSize and Steps in configuration file are"
                               "mutually exclusive")
        elif "StepSize" in settings:
            stepsize = float(settings["StepSize"])
        else:
            steps = int(settings["Steps"])
            stepsize = (stop - start) / steps
        
        # Infinite-Loop
        inf_cnt = 1
        while True:
            if infinite:
                appendix = "_{:0>2}".format(inf_cnt)
            else:
                appendix = ""
            
            name, ext = os.path.splitext(self.out_filename)
            
            with open(name + appendix + ext, "w") as outf:
                # Tabellenkopf
                print("# Config: {}".format(self.config_filename), file=outf)
                print("# Date: {}".format(asctime()), file=outf)
                print("# Center: {}".format(self.vna.get_center()), file=outf)
                print("# Span: {}".format(self.vna.get_span()), file=outf)
                print("# Points: {}".format(self.vna.get_points()), file=outf)
                
                if checkmode:
                    print("# P\tf\tf_ref\tfreq-t_ref", file=outf)
                else:
                    print("# P\tf", file=outf)
                
                pos = start
                while stop - pos > -1E-6:
                    print("Measuring: d = {} mm".format(pos))
                    
                    if checkmode:
                        f_ref = self.get_freq_at(cm_reference)
                        if rc_mode:
                            self.vna.write_raw(rc_folder + "{:0>4}mm_ref".format(int(pos)) + appendix + ext)
                    freq = self.get_freq_at(pos)
                    if rc_mode:
                        self.vna.write_raw(rc_folder + "{:0>4}mm".format(int(pos)) + appendix + ext)
                    
                    if checkmode:
                        print("{0:.3f}\t{1}\t{2}\t{3}".format(pos, freq, f_ref, freq - f_ref),
                              file=outf)
                    else:
                        print("{0:.3f}\t{1}".format(pos, freq), file=outf)
                    
                    pos += stepsize
                    outf.flush()
            
            inf_cnt += 1
            self.motor.move_to(start)
            
            if not infinite: break
        
    def get_freq_at(self, pos):
        delay = float(self.config["MEASUREMENT"]["Delay"])
        average = int(self.config["VNA"]["Average"])
        
        self.motor.move_to(pos)
        while self.motor.is_moving():
            sleep(0.1)
        sleep(delay)
        self.vna.measurecycles()
        freq, refl = self.vna.mark[1].search_min()
        
        return freq

if __name__ == "__main__":
    parser = ArgumentParser(description="Bead-Pull measurement application.")
    parser.add_argument("config",
                        metavar="CONFIG", action="store", type=str,
                        help="Measurement configuration file")
    parser.add_argument("file",
                        metavar="FILE", action="store", type=str,
                        help="Outfile")
    args = parser.parse_args()
    
    measurement = Stoerkoerpermessung(args.config, args.file)
    measurement.measure()
