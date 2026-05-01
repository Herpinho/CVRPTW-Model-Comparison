include "globals.mzn";

% Defining Variables
int: custcount;
int: vehicount;
float: capacity;

set of int: Customers = 1..custcount;
set of int: Nodes = 0..custcount+1; 

float: max_time = due[0];

array[Nodes] of float: x;
array[Nodes] of float: y;
array[Nodes] of float: demand;
array[Nodes] of float: ready;
array[Nodes] of float: due;
array[Nodes] of float: service;

array[Nodes] of var Nodes: successor;
array[Nodes] of var 1..vehicount: vehicle;
array[Nodes] of var 0.0..max_time: arrival;
array[Nodes] of var 0.0..capacity: load;

%Constraints for the solver

constraint successor[custcount + 1] = 0;

constraint circuit(successor);

constraint forall(a in 0..custcount) (
    vehicle[successor[a]] = vehicle[a]
);

constraint forall(a in 0..custcount) (
    let {var Nodes: b = successor[a]} in
    vehicle[b] = vehicle[a]
);

constraint forall(i in Nodes) (
    arrival[i] >= ready [i] /\ arrival[i] <= due[i]
)

constraint forall(a in 0..custcount) (
    let {var Nodes: b = successor[a]} in
    arrival[b] >= arrival[a] + service[a] + dists[a,b]
);

constraint forall(a in 0..custcount) (
    let { var Nodes: b = successor[a]} in
    load[b] = (if b == 0 then 0 else load[a] + demand[b] endif)
);

%Map and distance array
array[Nodes, Nodes] of float: dists = array2d(Nodes, Nodes, [
    sqrt((x[i]-x[j])^2 + (y[i] - y[j])^2)
    | i, j in Nodes
]);

var float: score = sum(i in Nodes where i <= custcount) (
    dists[i, successor[i]]
);

solve minimize score;