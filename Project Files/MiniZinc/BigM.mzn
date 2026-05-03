include "globals.mzn";

% Defining Variables
int: custcount;
int: vehicount;
int: capacity;
int: depot = 1;

set of int: Customers = 2..custcount + 1;
set of int: Nodes = 1..custcount + 1;
set of int: Vehicles = 1..vehicount;

int: max_time = due[depot];

array[Nodes] of int: x;
array[Nodes] of int: y;
array[Nodes] of int: demand;
array[Nodes] of int: ready;
array[Nodes] of int: due;
array[Nodes] of int: service;

array[Vehicles, Nodes] of var Nodes: successor;
array[Vehicles, Nodes] of var 0..1000000: arrival;
array[Vehicles, Nodes] of var 0..capacity: load;

%Map creation and score calc
array[Nodes, Nodes] of int: dists = array2d(Nodes, Nodes, [
    round(sqrt((x[i]-x[j])^2 + (y[i]-y[j])^2)*100)
    | i, j in Nodes
]);

%Constraints for the solver

constraint forall(v in Vehicles) (
    subcircuit(row(successor, v))

);
constraint forall(c in Customers) (
    sum(v in Vehicles) (bool2int(successor[v, c] != c)) == 1
); 

constraint forall(v in Vehicles) (
    load[v, depot] = 0
);

constraint forall(v in Vehicles, i in Nodes) (
    let {var Nodes: j = successor[v,i]} in
    if i != j /\ j != depot then
        arrival[v,j] >= arrival[v,i] + service[i] + dists[i,j]
    else
        true
    endif
);
constraint forall (v in Vehicles, i in Nodes) (
    load[v,i] <= capacity
);
constraint forall(v in 1..vehicount-1) (
    lex_lesseq(row(successor, v), row(successor, v+1))
); 
constraint forall(v in Vehicles, i in Nodes) (
    let {var Nodes: j = successor[v,i]} in
    if j != i then
        load[v,j] = (if j == depot then 0 else load[v,i] + demand[j] endif)
    else
        true
    endif
);
constraint forall(v in Vehicles, i in Nodes) (
    arrival[v, i] >= ready[i] /\ arrival[v, i] <= due[i]
);
constraint forall(v in 1..vehicount-1) (
    (successor[v, depot] == depot) -> (successor[v+1, depot] == depot)
);
constraint forall(v in Vehicles) (
    (successor[v, depot] == depot) -> forall(c in Customers) (successor[v, c] == c)
);
var int: vehicle_penalty = sum(v in Vehicles) (
    bool2int(successor[v, depot] != depot) * 100000
);
var int: score = sum(v in Vehicles, i in Nodes) (
    dists[i, successor[v,i]]
) + vehicle_penalty;

solve :: int_search(array1d(successor), first_fail, indomain_min)
      :: restart_constant(100) 
      minimize score;
