import json
import os
import boto3
from boto3.dynamodb.conditions import Key, Attr
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.data_classes.api_gateway_proxy import Response

logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, context):
    query_params = event.get('queryStringParameters') or {}
    limit = int(query_params.get('limit', 10))
    last_evaluated_key = query_params.get('lastEvaluatedKey')
    host_id = query_params.get('hostId')
    category = query_params.get('category')
    sort_order = query_params.get('sortOrder', 'asc')

    scan_kwargs = {
        'Limit': limit
    }

    if last_evaluated_key:
        scan_kwargs['ExclusiveStartKey'] = json.loads(last_evaluated_key)

    if host_id:
        scan_kwargs['IndexName'] = 'hostId-index'
        scan_kwargs['KeyConditionExpression'] = Key('hostId').eq(host_id)

    if category:
        scan_kwargs['FilterExpression'] = Attr('category').eq(category)

    if sort_order == 'desc':
        scan_kwargs['ScanIndexForward'] = False

    try:
        response = table.scan(**scan_kwargs)
        items = response.get('Items', [])
        last_evaluated_key = response.get('LastEvaluatedKey')

        return Response(
            status_code=200,
            body=json.dumps({
                'items': items,
                'lastEvaluatedKey': last_evaluated_key
            })
        )

    except Exception as e:
        logger.error(e)
        return Response(
            status_code=500,
            body=json.dumps({"message": "Internal server error", "code": 500, "details": str(e)})
        )
