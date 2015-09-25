# Ansteuerung für:
# MForce MicroDrive Motion Control -- Schrittmotorcontroller
# MDrive 23 Plus Motion Control -- Motor mit integriertem Controller
# von Schneider Electric
# 
# benötigt: python3 & pyserial

from serial import Serial

class Motor:
    """Steuerung eines Motors an der seriellen Schnittstelle "serial"."""
    def __init__(self, ser, name):
        self.serial = ser
        self.name = name
        
        # SCALING: Proportionalitätskonstante zwischen Position in mm/cm/... und
        #          Anzahl von µSteps des Schrittmotors
        #          Beispiel: Spindel der Störkörpermessung: 0.005996 mm/µSteps
        #                    Verbindet Position des Störkörpers mit Anzahl der
        #                    Schritte des Motors
        self.scaling = 1.0
    
    # Für Bedeutung der Konfigurationdatei vgl. "stoerkoerper.conf" und die
    # Softwaredokumentation des Schrittmotorcontrollers
    def load_motor_config(self, file):
        """Lädt die Motorkonfiguration in "file" und überträgt sie an den Motor."""
        with open(file) as f:
            conf = [line.rstrip() for line in f if line != ""]
        
        for setting in conf:
            cmd = self.name + setting + "\n"
            self.serial.write(cmd.encode())
            self.serial.readline()
    
    def get(self, var):
        """Frägt die Variable "var" ab."""
        cmd = "{0}PR {1}\n".format(self.name, var) 
        
        self.serial.write(cmd.encode())
        # Response-Format: \r\n und dann RESPONSE\n
        self.serial.readline()
        response = self.serial.readline().decode()
        return response.rstrip()
    
    def move(self, pos):
        """Bewegt den Motor zu einer relativen Position "pos"."""
        P = int(1.0 * pos / self.scaling)
        cmd = "{0}MR {1}\n".format(self.name, P)
        
        self.serial.write(cmd.encode())
        self.serial.readline()
    
    def speed(self, speed):
        """Setzt den Motor auf die Geschwindigkeit "speed". Dies ist unabhängig
        von der gesetzten maximalen Geschwindigkeit."""
        SP = int(1.0 * speed / self.scaling)
        cmd = "{0}SL {1}\n".format(self.name, SP)
        
        self.serial.write(cmd.encode())
        self.serial.readline()
    
    def stop(self):
        """Stoppt den Motor."""
        cmd = "{0}SL 0\n".format(self.name)
        
        self.serial.write(cmd.encode())
        self.serial.readline()
    
    def move_to(self, pos):
        """Bewegt den Motor zu einer absoluten Position."""
        P = int(1.0 * pos / self.scaling)
        cmd = "{0}MA {1}\n".format(self.name, P)
        
        self.serial.write(cmd.encode())
        self.serial.readline()
    
    def reset_pos(self):
        """Setzt den Nullpunkt an die aktuelle Position."""
        cmd = "{0}P 0\n".format(self.name)
        
        self.serial.write(cmd.encode())
        self.serial.readline()
    
    def pos(self):
        """Position des Motors."""
        P = int(self.get("P"))
        return P * self.scaling
    
    # Nur für die Abstimmstempel
    def is_at_limit_high(self):
        """Abfrage des Schalters der oberen Begrenzung."""
        I1 = int(self.get("I1"))
        return bool(I1)
    
    # Nur für die Abstimmstempel
    def is_at_limit_low(self):
        """Abfrage des Schalters der unteren Begrenzung."""
        I2 = int(self.get("I2"))
        return bool(I2)
    
    # Nur für die Abstimmstempel
    def analog_pos(self):
        """Auslese der analogen Position (Potentiometer)."""
        I5 = int(self.get("I5"))
        return I5
    
    def is_moving(self):
        """Auslese des Bewegungszustandes des Motors."""
        MV = int(self.get("MV"))
        return bool(MV)


# Beispiel
if __name__ == '__main__':
    ser = Serial('/dev/ttyUSB0', 9600, timeout=1.0)
    ser.flushInput()
    ser.flushOutput()
    
    mo = Motor(ser, "D")
    mo.load_motor_config("stoerkoerper.conf")
    mo.scaling = 0.005996
