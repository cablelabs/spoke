#! /bin/bash

curl -d '{"pub_key":"pk1"}' http://localhost:8088/register
curl -d '{"pub_key":"pk2"}' http://localhost:8088/register
curl -d '{"pub_key":"pk3"}' http://localhost:8088/register
echo


aggregate1=10
aggregate2=20
aggregate3=60

R=$RANDOM

# initiator
aggregate=`echo "$R+$aggregate1" | bc` 
echo "Posting $aggregate 1->2"
curl -s -d '{"aggregate":"'$aggregate'","from_node":1,"to_node":2}' http://localhost:8088/post_aggregate && echo

# client 2 
AGG=`curl -s -d '{"node":2}' http://localhost:8088/get_aggregate`
aggregate=`echo -e "$AGG" | jq -r .aggregate`
aggregate=`echo "$aggregate+$aggregate2" | bc` 
echo "Posting $aggregate 2->3"
curl -s -d '{"aggregate":"'$aggregate'","from_node":2,"to_node":3}' http://localhost:8088/post_aggregate && echo

# client 3 
AGG=`curl -s -d '{"node":3}' http://localhost:8088/get_aggregate`
aggregate=`echo -e "$AGG" | jq -r .aggregate`
aggregate=`echo "$aggregate+$aggregate3" | bc` 
echo "Posting $aggregate 3->1"
curl -s -d '{"aggregate":"'$aggregate'","from_node":3,"to_node":1}' http://localhost:8088/post_aggregate && echo

# initiator 
AGG=`curl -s -d '{"node":1}' http://localhost:8088/get_aggregate`
aggregate=`echo -e "$AGG" | jq -r .aggregate`
average=`echo "($aggregate-$R)/3" | bc` 
echo "Got average $average"
