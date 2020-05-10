# Mobility Test 2

Test nodes move around randomly and form new connections.

1. 50 nodes are distributed on a 1km x 1km square
2. for distances of 50m to 400m in steps of 50m do six times:
    1. move nodes in random directions of current distance
    2. 150 nearest links are established
    3. wait 10 seconds
    4. 200 pings are send from a random source node to random destination node
    5. the percentage of the arrived pings is added to the score value

## Run

* remove remaining `*.csv` files in this directory
* execute `sudo ./run.py` to run the test (will take a long time).
* `./plot.sh` will create graphs using gnuplot