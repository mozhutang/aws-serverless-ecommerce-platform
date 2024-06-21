import json
import os
import boto3
from boto3.dynamodb.conditions import Attr
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
    city = query_params.get('city')
    category = query_params.get('category')
    min_price = query_params.get('minPrice')
    max_price = query_params.get('maxPrice')

    scan_kwargs = {
        'Limit': limit
    }

    if last_evaluated_key:
        scan_kwargs['ExclusiveStartKey'] = json.loads(last_evaluated_key)

    filter_expression = []

    if city:
        filter_expression.append(Attr('city').eq(city))
    if category:
        filter_expression.append(Attr('category').eq(category))
    if min_price:
        filter_expression.append(Attr('price').gte(int(min_price)))
    if max_price:
        filter_expression.append(Attr('price').lte(int(max_price)))

    if filter_expression:
        scan_kwargs['FilterExpression'] = filter_expression.pop()
        for expr in filter_expression:
            scan_kwargs['FilterExpression'] &= expr

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
