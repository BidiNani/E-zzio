from datetime import datetime


class MemoryHistory:


    def __init__(self):

        self.history=[]



    def add(self,event):

        self.history.append({

            "timestamp":
                datetime.now().isoformat(),

            "event":
                event

        })



    def list(self):

        return self.history
