import json
import boto3  
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection
import time

def getMessageFromLex(q):
    client = boto3.client('lexv2-runtime')
    

    # Submit the text 'I would like to see a dentist'
    response = client.recognize_text(
        botId='IJWVSWHX81',
        botAliasId='VGU7EELBND',
        localeId='en_US',
        sessionId=str(time.time()),
        text=q)
        
    print(response)
    
    out = []
    description1 = response['interpretations'][0]['intent']['slots']['Description']
    description2 = response['interpretations'][0]['intent']['slots']['Description2']
    
    if description1:
        out.append(description1['value']['resolvedValues'][0])

    if description2:
        out.append(description2['value']['resolvedValues'][0])

    #hack to make queries like "CATS" return pictures labeled as CAT
    for i in range(len(out)):
        word = out[i]
        if word[-1] == "s" or word[-1] == "S":
            out[i] = word[:len(word)-1]

    return out

def query(parsed_query):

    service = 'es'
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, "us-east-1", service, session_token=credentials.token)

    #host = 'search-photos-tkylqog3r54ymwr2fkodktfp74.us-east-1.es.amazonaws.com' 
    host = 'search-myopensearchdom-jbgzixfdropm-s4ro6vprjsl33ultx3x7p575mm.us-east-1.es.amazonaws.com'
    search = OpenSearch(
        hosts = [{'host': host, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )
    
    query_def = {
      "query": {
        "simple_query_string": {
          "query": '+'.join(parsed_query),
          "fields": ["labels"]
        }
      }
    }

    response = search.search(
        body = query_def,
        index = "photos"
    )
    print(response)
    
    base_url = 'https://ccbd-hw2-photos-cf.s3.amazonaws.com/{}'
    
    out = map(lambda x: {'url': base_url.format(x['_source']['objectKey']), 'labels' : x['_source']['labels']}, response['hits']['hits'])
    
    return(list(out))
    
def lambda_handler(event, context):
    print(event)
    
    query_string = event['queryStringParameters']['q']
    print(query_string)
    
    parsed_query = getMessageFromLex(query_string)
    
    print(parsed_query)
    
    out = []
    if parsed_query:
        out = query(parsed_query)
    
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
        },
        'body': json.dumps(out)
    }
