import json
import requests
from pprint import pprint
import numpy as np
# from matplotlib import pyplot as plt
import datetime

url = 'https://api.warmbeachtides.org'
apikey = 'dpifJuDLFr6UcdGv7Iq742T5ZJ3fHbuKa6I0zYBq'


# a1 = 11
# b1 = 1.1
# c1 = 1.5
# a2 = 9.5
# b2 = 0.5
# c2 = 0
# x = np.arange(0, 4*np.pi, np.pi/72)
# y = a1*np.cos(b1*x+c1) + a2*np.cos(b2*x+c2)
# print(len(x))


# now = datetime.datetime.now()
# timeStart = now.replace(hour=0, minute=0, second=0, microsecond=0)

# records = []
# for i in range(len(y)):
#     timestamp = timeStart + datetime.timedelta(minutes=i*5)
#     timestamp = timestamp.timestamp()
#     record = {'time': int(timestamp), 'data': int(y[i])}
#     records.append(record)

# print(timeStart)
# pprint(records)

# plt.plot(x, y)
# plt.show()

# sensorData = {"id": "abc123",
#               "records": records}


              # [
              #   {"time": "12345678", "data": 123},
              #   {"time": "1234567",  "data": 456}]}


# deviceData = {"id": "abc123",
#               "time": 123456,
#               "sensorPollingPeriod": 10000,
#               "cloudUpdatePeriod": 20000,
#               "numSamplesPerPoll": 5,
#               "deviceInfoUpdatePeriod": 2000,
#               "batteryPercent": 94.2,
#               "queueSize": 5}

# pprint(sensorData)

# res = requests.post(f"{url}/login", headers={'x-api-key': apikey})
# res = requests.get(f"{url}/sensor-data?limit=3", headers={'x-api-key': apikey})
# res = requests.get(f"{url}/sensor-data?timestamp_lt=2021-04-05T00:00:00", headers={'x-api-key': apikey})
# res = requests.get(f"{url}/device-data?id=1", headers={'x-api-key': apikey})
# res = requests.post(f"{url}/sensor-data", headers={'x-api-key': apikey}, data=json.dumps(sensorData))
# res = requests.post(f"{url}/device-data", headers={'x-api-key': apikey}, data=json.dumps(deviceData))
# res = requests.delete(f"{url}/sensor-data?bryce=yes", headers={'x-api-key': apikey})
pprint(res.content)
# pprint(json.loads(res.content))
