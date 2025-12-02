#---------------If potentiometer.read() is between 0 and 1023 you can set a new distance between the numbers. For example, 10-100.---------------
class Map:
    def map(self, x, in_min, in_max, out_min, out_max): # returns an integer
        return (x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min

#---------------If potentiometer.read() is between 0 and 1023 you can set a new distance between the numbers. F