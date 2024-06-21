import json
import os
import boto3
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
    listing_id = event['pathParameters']['listingId']

    try:
        response = table.get_item(Key={'listingId': listing_id})
        item = response.get('Item')

        if not item:
            return Response(
                status_code=400,
                body=json.dumps({"message": "Invalid listing ID", "code": 400, "details": "Listing ID provided is not valid."})
            )

        return Response(
            status_code=200,
            body=json.dumps(item)
        )

    except Exception as e:
        logger.error(e)
        return Response(
            status_code=500,
            body=json.dumps({"message": "Internal server error", "code": 500, "details": "An unexpected error occurred while processing the request."})
        )
