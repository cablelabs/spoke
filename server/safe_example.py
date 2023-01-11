#! /usr/bin/env python3

from safe import Controller

import random

controller = Controller()


controller.register("pk1")
controller.register("pk2")
controller.register("pk3")

aggregate1 = 10
aggregate2 = 20
aggregate3 = 60

R = random.randint(1,100000)

# initiator
aggregate = R + aggregate1
print(f"Posting {aggregate} 1->2")
controller.post_aggregate(aggregate,1,2)

# client 2 
result = controller.get_aggregate(2)
aggregate = result["aggregate"]
aggregate += aggregate2
print(f"Posting {aggregate} 2->3")
controller.post_aggregate(aggregate,2,3)

# client 3
result = controller.get_aggregate(3)
aggregate = result["aggregate"]
aggregate += aggregate3
print(f"Posting {aggregate} 3->1")
controller.post_aggregate(aggregate,3,1)

# initiator
result = controller.get_aggregate(1)
aggregate = result["aggregate"]
aggregate = aggregate - R

print(f"Got average {aggregate/3}") 



 


