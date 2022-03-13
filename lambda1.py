import json
import boto3  
from requests_aws4auth import AWS4Auth
from datetime import datetime
from opensearchpy import OpenSearch, RequestsHttpConnection

def get_rek_labels(bucket, name):
    client = boto3.client("rekognition")
    response = client.detect_labels(Image = {"S3Object": {"Bucket":bucket, "Name": name}}, MaxLabels=5,  MinConfidence=70)
    print(response)
    labels = map(lambda x: x['Name'], response['Labels'])
    return list(labels)
    
def get_s3_meatadata(bucket, name):
    client = boto3.client('s3')
    response = client.head_object(Bucket=bucket, Key=name)
    print(response)
    metadata = response['Metadata']
    custom_labels = []
    if 'customlabels' in metadata:
        custom_labels = metadata['customlabels'].split(',')
    return custom_labels
    
def store_object(bucket, name, labels):
    to_store = {
        "objectKey": name,
        "bucket": bucket,
        "createdTimestamp": datetime.now().strftime("%d-%b-%Y (%H:%M:%S.%f)"),
        "labels": labels
    }
    print(to_store)
    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, "us-east-1", service, session_token=credentials.token)

    host = 'search-photos-tkylqog3r54ymwr2fkodktfp74.us-east-1.es.amazonaws.com' 
    search = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    r =search.index(index="photos", doc_type="_doc", id=name, body=to_store)
    print(r)
    
def lambda_handler(event, context):
    print(event)
    bucket = event['Records'][0]['s3']['bucket']['name']
    name = event['Records'][0]['s3']['object']['key']
    print("Bucket {}, Name {}".format(bucket, name))
    rek_labels = get_rek_labels(bucket, name)
    print(rek_labels)
    custom_labels = get_s3_meatadata(bucket, name)
    labels = rek_labels + custom_labels
    store_object(bucket, name, labels)
    
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
