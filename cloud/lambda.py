import boto3
import json

from pprint import pprint

def postWaterLevelData(event, context):
    data = json.loads(event['body'])
    pprint(data)

    # Write data to Timestream
    client = boto3.client('timestream-write')
    response = client.write_records(DatabaseName='MudFlatsTideData',
                                    TableName='WaterLevel',
                                    CommonAttributes={'Dimensions': [
                                            {'Name': 'deviceID', 'Value': '12', 'DimensionValueType': 'VARCHAR'},
                                        ],},
                                    Records=[{
                                            'Dimensions': [
                                                {
                                                    'Name': 'timestamp',
                                                    'Value': 'today',
                                                    'DimensionValueType': 'VARCHAR'
                                                },
                                            ],
                                            'MeasureName': 'dist',
                                            'MeasureValue': '12',
                                            'MeasureValueType': 'DOUBLE',
                                        },
                                    ]
                                    )
    return {
        'statusCode': 200,
        'body': 'OK'
    }


def test():
    jsonData = """
               [
                 {"id": "<UUID>", "timestamp":"<ISO FORMAT UTC>", "data": ["<FLOAT>"]},
                 {"id": "<UUID>", "timestamp":"<ISO FOMMAT UTC>", "data": ["<FLOAT>"]}
               ]
               """

    event = {'resource': '/tide-data',
             'path': '/tide-data',
             'httpMethod': 'POST',
             'headers': None,
             'multiValueHeaders': None,
             'queryStringParameters': None,
             'multiValueQueryStringParameters': None,
             'pathParameters': None,
             'stageVariables': None,
             'body': jsonData,
             'isBase64Encoded': False
             }
    postWaterLevelData(event, None)


if __name__ == '__main__':
    test()
