# Bitcoin GPU miner
***Bitcoin stratum Nvidia GPU miner***

Bitcoin GPU mining is not profitable nowadays.

This source can help you understand what exactly happens between a bitcoin stratum pool server and a miner.

For the stratum poll server, you can use ***[this source]***(https://github.com/tokimay/bitcoin_stratum_server). 


Install requirement: <br />
````shell
$ pip install numpy
$ pip install pycuda
````
Run:  <br />
````shell
$ python3 bitcoin_GPU_miner.py -u YOUR_BITCOIN_ADDRESS -p YOUR_MINING_PASSWORD -o STRATUM_SERVER_ADDRESS:PORT
````