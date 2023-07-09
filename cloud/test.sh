#!/bin/bash

 
# TODO: stack status
#


# Clean up any leftover test data
./admin.py db-data       \
    --device test-device \
    --delete             \
    --timestamp '>0'     \
    --limit 100


# TODO: add config-table clears, writes, & reads

# Insert new test data using db commands
numInserts=5
for run in $(seq $numInserts); do
    ./admin.py db-data         \
        --device test-device   \
        --post                 \
        --timestamp `date +%s` \
        --data "source=db-data;run=$run;data=[1,2,3]"
    sleep 1.5
done

# List current data using db commands
res=$(./admin.py db-data       \
          --device test-device \
          --get                \
          --timestamp ">0"     \
          --limit 100)

numRead=$(($(echo "$res" | wc -l)-2))
echo "Wrote $numInserts; read $numRead"
if [ ! $numRead -eq $numInserts ]; then
    echo "ERROR"
    exit
fi

# Insert new test data using lambda commands
# using jq to build the JSON data structure.
numInserts2=5
dataList='{}'
dataList=$(echo $dataList | jq '. += {"name": "test-device", "data": []}')
for run in $(seq $numInserts2); do
    data='[]'
    vals='{}'
    vals=$(echo $vals | jq '. += {"source": "lambda-invoke"}')
    vals=$(echo $vals | jq '. += {"data": "[1,2,3]"}')
    vals=$(echo $vals | jq ". += {\"run\": \"$run\"}")
    data=$(echo $data | jq ". += [[$(date +%s), $vals]]")
    dataList=$(echo $dataList | jq ".data += $data")
    sleep 1.5
done
./admin.py lambda-invoke   \
    --post                 \
    --data "$dataList"

# List current data using lambda commands
res=$(./admin.py lambda-invoke \
          --device test-device \
          --get                \
          --timestamp ">0"     \
          --limit 100)

numRead=$(($(echo "$res" | wc -l)-2))
numCheck=$(($numInserts+$numInserts2))
echo "Wrote $numInserts2 more; read $numRead"
if [ ! $numRead -eq $numCheck ]; then
    echo "ERROR"
    exit
fi











# Clean up any remaining test data
printf "\n\nCleaning Up...\n"
./admin.py db-data       \
    --device test-device \
    --delete             \
    --timestamp '>0'     \
    --limit 100
