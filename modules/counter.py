class MultiCounter:
    def __init__(self):
        self.counters = {}
    
    def counter(self, counter_id, sleep):
        if counter_id not in self.counters:
            self.counters[counter_id] = 0
            
        if self.counters[counter_id] >= sleep:
            self.counters[counter_id] = 0
            return True
        else:
            self.counters[counter_id] += 1
            return False
            
        
    
    def reset(self, counter_id):
        if counter_id in self.counters:
            self.counters[counter_id] = 0
