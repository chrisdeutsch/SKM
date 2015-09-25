# Serielle Ansteuerung für den VNA:
# Rohde & Schwarz ZVC 1127.8600.62
# 
# benötigt: python3 & pyserial

from serial import Serial
from time import sleep, asctime
from math import sqrt, atan2
from struct import unpack

class VNA:
    """Klasse zur Steuerung des vektoriellen Netzwerkanalysators."""
    def __init__(self, port, baudrate):
        self.serial = Serial(port, baudrate)
        self.serial.flushInput()
        self.serial.flushOutput()
        
        # Lokale Benutzeroberfläche des VNA sperren
        self.cmd("@REM")
        
        # Markerobjekte 1 - 4 in Dictionary eintragen
        self.mark = dict()
        for i in range(1,5):
            self.mark[i] = Marker(self.serial, i)
    
    def __del__(self):
        self.serial.flush()
        del self.serial
    
    def cmd(self, command):
        command += "\n"
        self.serial.write(command.encode())
    
    # Einstellung des Frequenzbereichs
    # Die Frequenz "freq" wird gegeben als String mit Einheit:
    # z.B.: "1.55GHz", "50000Hz", ...
    def set_center(self, freq):
        """ Setzt die Mittenfrequenz des Messbereichs """
        self.cmd("SENSE:FREQ:CENTER " + str(freq))
    
    def get_center(self):
        """ Fragt die Mittenfrequenz des Messbereichs ab """
        self.cmd("SENSE:FREQ:CENTER?")
        center = self.serial.readline().decode()
        return float(center)
    
    def set_span(self, freq):
        """ Setzt die Ausdehnung des Messbereichs um die Mitte """
        self.cmd("SENSE:FREQ:SPAN " + str(freq))
    
    def get_span(self):
        """ Fragt die Ausdehnung des Messbereichs um die Mitte ab """
        self.cmd("SENSE:FREQ:SPAN?")
        span = self.serial.readline().decode()
        return float(span)
    
    def set_start(self, freq):
        """ Setzt die Startfrequenz des Messbereichs """
        self.cmd("SENSE:FREQ:START " + str(freq))
    
    def get_start(self):
        """ Fragt den Start des Messbereichs ab """
        self.cmd("SENSE:FREQ:START?")
        start = self.serial.readline().decode()
        return float(start)
    
    def set_stop(self, freq):
        """ Setzt die Stopfrequenz des Messbereichs """
        self.cmd("SENSE:FREQ:STOP " + str(freq))
    
    def get_stop(self):
        """ Fragt das Ende des Messbereichs ab """
        self.cmd("SENSE:FREQ:STOP?")
        stop = self.serial.readline().decode()
        return stop
    
    def set_avg(self, avg):
        """ Aktiviert (avg > 1) / Deaktiviert (avg <= 1) die Mittelwertbildung über
        mehrere Sweeps. """
        if avg > 1:
            self.cmd("SENSE:AVERAGE:COUNT " + str(avg))
            self.cmd("SENSE:AVERAGE:STATE ON")
            self.cmd("SENSE:AVERAGE:CLEAR")
        else:
            self.cmd("SENSE:AVERAGE:COUNT 1")
            self.cmd("SENSE:AVERAGE:STATE OFF")
            self.cmd("SENSE:AVERAGE:CLEAR")
    
    def get_avg(self):
        """ Fragt die Anzahl der Mittelwertbildungen über den Messbereich ab """
        self.cmd("SENSE:AVERAGE:COUNT?")
        avg = self.serial.readline().decode()
        return int(avg)
    
    def reset_avg(self):
        """ Startet die Mittelwertbildung neu. """
        self.cmd("SENSE:AVERAGE:CLEAR")
    
    def set_points(self, pts):
        """ Setzt die Anzahl der Messpunkte auf dem Messbereich (Range: 3 bis 2001). """
        if pts > 2001:
            pts = 2001
        elif pts < 3:
            pts = 3
        self.cmd("SENSE:SWEEP:POINTS " + str(pts))
    
    def get_points(self):
        """ Fragt die Anzahl der Messpunkte auf dem Messbereich ab """
        self.cmd("SENSE:SWEEP:POINTS?")
        pts = self.serial.readline().decode()
        return int(pts)
    
    def set_power(self, P):
        """ Setzt die Leistung des Messsignals in Einheiten von dBm (Range: -17 bis 6) """
        if P > 6:
            P = 6
        elif P < -17:
            P = -17
        self.cmd("SOURCE:POWER " + str(P) + "dBm")
    
    def autoscale(self):
        """ Automatische Skalierung der Y-Achse """
        self.cmd("DISP:TRAC:Y:AUTO ONCE")
    
    def measurecycles(self):
        """ Wartet bis die Mittelwertbildung über "avg"-Sweeps abgeschlossen ist. """
        self.reset_avg()
        avg = self.get_avg()
        sleep(self.get_sweeptime() * (avg + 1))
    
    def get_sweeptime(self):
        """ Liefert die Dauer eines Sweeps in Sekunden """
        self.cmd("SENS:SWEEP:TIME?")
        time = self.serial.readline().decode()
            
        return float(time)
    
    def read_raw_ascii(self):
        """ Ließt die komplexen Datenpunkte des aktuellen Messbereichs aus. Daten: ASCII (ineffizient) """
        self.cmd("FORMAT:DATA ASCII")
        self.cmd("TRAC? CH1DATA")
        
        raw = self.serial.readline().decode().rstrip()
        raw = raw.split(",")
        
        # Daten werden gesendet als: {real_1, imag_1, real_2, imag_2, ...}
        # Extended Slice: [start:stop:step] ([0::2] / [1::2] jedes zweite Item vom ersten/zweiten Element)
        re = [float(x) for x in raw[0::2]]
        im = [float(y) for y in raw[1::2]]
        
        # Zip erstellt aus zwei Listen eine Liste von Tupeln
        return list(zip(re, im))
    
    def read_raw(self):
        """ Ließt die komplexen Datenpunkte des aktuellen Messbereichs aus. Daten: 64-bit float. """
        self.cmd("FORMAT:DATA REAL,64")
        self.cmd("TRAC? CH1DATA")
        
        # Markiert den Anfang des binären Datenstroms
        byte = self.serial.read()
        if byte.decode() == "#":
            # Längenzähler Länge
            length = int(self.serial.read().decode())
            
            # Länge des Datenstroms
            data_length = int(self.serial.read(length).decode())
            
            # Anzahl der Datenpunkte: 8 bytes (64-bit float) * 2 (komplex)
            data_pts = data_length // 16
            
            ret = list()
            for i in range(data_pts):
                re, = unpack('<d', self.serial.read(8))
                im, = unpack('<d', self.serial.read(8))
                ret.append((re,im))
        else:
            return None

        self.serial.readline()
        return ret
    
    def read_amp_phase(self):
        """ Ließt die komplexen Datenpunkte des aktuellen Messbereichs aus und konvertiert diese
        in Polardarstellung. """
        raw = self.read_raw()
        # Berechnung in Polarkoordinaten
        return [(sqrt(re*re + im*im), atan2(im, re)) for (re,im) in raw]
    
    def write_raw(self, file):
        """ Schreibt die komplexen Datenpunkte des aktuellen Messbereichs in die Datei 'file'. """
        raw = self.read_raw()
        
        with open(file, "w") as f:
            f.write("# Date: {}\n".format(strftime("%d/%m/%Y-%H:%M:%S")))
            f.write("# Center: {}\n".format(self.get_center()))
            f.write("# Span: {}\n".format(self.get_span()))
            f.write("# Points: {}\n".format(self.get_points()))
            f.write("# Real:\tImag:\n")
            
            for line in raw:
                real, imag = line
                f.write("{}\t{}\n".format(real, imag))

class Marker:
    def __init__(self, serial, num):
        self.serial = serial
        self.number = num
        
        self.prefix = "CALC:MARK{}:".format(self.number)
    
    def search_min(self):
        self.cmd("MIN")
        self.cmd("SEARCH")
        
        return self.get_pos()
    
    def search_max(self):
        self.cmd("MAX")
        self.cmd("SEARCH")

        return self.get_pos()
    
    def next_left(self):
        self.cmd("SEARCH:LEFT")
        
        return self.get_pos()
    
    def next_right(self):
        self.cmd("SEARCH:RIGHT")

        return self.get_pos()
    
    def target(self, t):
        self.cmd("FUNC:SEL TARG")
        self.cmd("FUNC:TARG " + str(t))
        self.cmd("SEARCH")
        
        return self.get_pos()
        
    def get_pos(self):
        self.cmd("X?")
        x = self.serial.readline().decode()
        
        self.cmd("Y?")
        y = self.serial.readline().decode()
        
        return float(x), float(y)
    
    def cmd(self, command):
        cmd = self.prefix + command + "\n"
        self.serial.write(cmd.encode())


# Beispiel: Güteberechnung durch Marker
if __name__ == "__main__":
    vna = VNA("/dev/ttyUSB1", 57600)
    sleep(1)

    fr, refl = vna.mark[1].search_min()
    print("f = " + str(fr) + " Hz")
    
    kappa = (1 - refl)/(1 + refl)
    t = sqrt(kappa*kappa + 1) / (kappa + 1)
    
    f_lo, _ = vna.mark[2].target(t)
    
    vna.mark[3].target(t)
    
    f_hi, _ = vna.mark[3].next_right()
    
    df = f_hi - f_lo
    Q = fr/df * (1+kappa)
    print("df = " + str(df) + " Hz")
    print("Q = " + str(Q))
    
    del vna
