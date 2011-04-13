#! /usr/bin/env python

import hashlib
import time
import uuid

class APIKey:
    def main(self):
        self.genkey()
        
    def genkey(self):
        u = str(uuid.uuid4())
        key = hashlib.sha1(str(time.time())+u).hexdigest()
        return key
        
if __name__ == "__main__":
    print APIKey().genkey()
