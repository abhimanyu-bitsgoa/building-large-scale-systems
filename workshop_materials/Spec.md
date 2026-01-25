Let's refactor the current workshop material into selected labs that are easier to demonstrate and follow by the students in the span of 6 hrs along with the teaching.

I don't want you to modify things inside the workshop_materials, will use this for review purposes till we finalise the lab code in this new format and then remove the workshop_Materials.

Here is the plan for this new workshop:

1. Create a directory called labs at the same level you have the folder workshop_materials.
2. Have the following labs inside it:
	1. scalability
	2. replication
	3. distributed-kvstore
NOTE: Make sure that the code changes that you are doing below are easier to understand and don't do overly complicated & verbose things if you don't need to & if similar functionality can be achived in simlar ways, suggest and use those.

Below is the step by step design for all the labs:

3. scalability:
3.a. The 01_nodes have good client and the node implementation. Copy them verbatim in this.
3.b. Now the goal is to showcase load balancing & rate limiting.
3.c. I will use the current node.py and client.py implementation to show that the process is being chocked with the concurrent requests for the client and there is so much you can do by increasing the workers in one server. So we can spawn multiple terminals at different ports mimicing different servers. Each of these servers will have different worker capacity. This will depict a heterogeneos compute. So when I will ask the students to implement a round robin load balancing algorithm. The current client.py already has this as node = NODES[count % len(NODES)] line. Don't modify the client.py unnecessarily and complicated change, see if you can abstrate this load blancing behaviour to a sepearte module called load_balancer.py that contains strategies for load balancing.
For round robin strategy have the current line as the implementation and for the other startegy, have the algorithm that prioritizes the node giving faster response time and less number of active requests.  If you can refactor the client with very mininmal and easy changes to use loadbalancing as a middleware, do that. Make sure that you show the ascii bar chart like in visualize_load_balance.py so that people can see the before and after effect of changing the load balancing algoritms.
3.d. For the rate limiting part, again, have a module rate_limiter.py that uses strategy pattern like the load_balancer.py. It can be a middleware too. Now implement the fixed windown algorithm. Have a small logical section in this that you think I can mark as todo. Don't leave this empty right now, just mark it. Just have this strategy for rate limiting.
Now the way I want to show this is, students will open 2 terminals, one that will set the concurrency to more than the fixed value that will be allowed and another one with the allowable limit, the server should show per request which one it is rejecting and which one it is accepting and the clients terminal should also get the correspoding resposne and the error code. The client.py shall be modified a bit to take in a --rate 1 that means there should be a wait of 1 sec in every request. There is no flow control for concurrent clients like this, and they will bomobard the server recieving rate limting errors
In the node.py make sure that you accept the  --rate-limit <STRATEGY> --load-balance=STRATEGY flags for running the request with these features.
Example: @rate_limited decorator in node.py and @load_balancer decorator will enable both on the node.py
The ASCII bar chart is great. Enhance it by showing HTTP 429 (Too Many Requests) counts in a separate red bar so students see the rate limiter actually dropping traffic.
Make a readme file that contains all the instructions to start this and demo this so that it is easier to follow for the students.

4. replication
4.a. The node.py that we worked in scalabily let's use the same module to iterate upon as this module already contains the in memory data store that we can use, because it already is storing data in the in memeory dict. This is the normal node.py that don't have the complexity and integration points for the load balancers & rate limiters.
4.b. Let's create a single-leader application based on the node.py. Create coordinator.py this will be responsible for starting leader and followers. It contains a static mapping of the leader and all the followers, can this is displayed to the user with the port number. This is an interactive display that will show the write percolation on the follower node and read traffic too. There should be commands that can turnup and turndown nodes in coordinator.py and the resultant should show the effect on the display and related visualisations.
When the user will start this  coordinator.py --replication <strategy> which will be single leader and multi followers, the system will start N+1 processes (1 leader and N followers) on different port numbers. When you do a write on coordinator.py, it will transfer the write to the leader and then it will percolate with a small delay on all the follower nodes via leader. The write path, the leader will wait for the ack from all the followers. Make read and write quorum configurable. So if it is defined W should be min success writes then W replicas shall be written with the data along with the leader. Now when the request for read will be send to the coordinator, read will be served by R followers accoridn to the quorum. coordinator is the one that will ensure that the stale read is not reported.
Make a readme file that contains all the instructions to start this and demo this so that it is easier to follow for the students.


5. distributed-kvstore
We have iteratively built the distrited key value store above partly. We need the students to feel that all these efforts have been converged in this direction now.
So the implementation should draw from the code parts above & should not have divergent implementations if not required. Make the code simple and easy to work with.
Make sure that you reuse the code that was used in above modules, so that the students don't have to understand different code. You can make some necessary modifications for harmonising & combining for things like say the gateway.py but keep it as such that the students who have followed the above modules find it easier to follow this.
We will implement the following features:

- gateway.py This module holds the logic for load_balancer.py and rate_limiter.py that were coded above. This will make it easier to follower and see the responsibility segrigation. The request will land on this from the client.
Ensure gateway.py literally imports from labs.scalability.load_balancer import .... This proves to students that the code they wrote 3 hours ago is production-ready.
Just like Example: @rate_limited decorator in node.py and @load_balancer decorator will enable both on the node.py, it can be the same for gateway.py and then the node.py can have @gateway as decorator.

- coordinator.py, node.py, client.py will be similar to the above.

- Let's demo the scenerio in which the follower is dead & you need to bring up another follower. Take inspiration from workshop_materials/11_membership on how to interactively show the registry of the new follwoers and interactive status. You should include logic to send the heartbeats in the node.py themselves, and a separate registry.py and visualiser for the membership just like in workshop_materials/11_membership. So in a nutshell, as the coordinator.py will spawn more processes it will tell registry about the current nodes and then when the followers are killed, registry will tell the coordinator.py to start a new node. There is an additinal module called catchup.py that can be hooked to the coordinator.py who brings the new follower with the same data as the leader of the cluster.

This way we have finally created a fault tolerant distributed key value store.
workshop_materials/23_resilient_system shows a /graudate easter egg. Show the exact same message to the user when they hit the gateway.py with this.

Make a readme file that contains all the instructions to start this and demo this so that it is easier to follow for the students.