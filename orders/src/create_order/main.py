import json
import os
import uuid
from datetime import datetime
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
def handler(event: APIGatewayProxyEvent, context):
    try:
        body = event.json_body

        order_id = str(uuid.uuid4())
        user_id = body['userId']
        order_type = body['orderType']
        detail_id = body['detailId']
        start_date = body.get('startDate')
        end_date = body.get('endDate')
        date = body.get('date')
        time = body.get('time')
        total = body['total']
        additional_fees = body['additionalFees']
        host_id = body['hostId']

        item = {
            'orderId': order_id,
            'userId': user_id,
            'Type': order_type,
            'listingId': detail_id,
            'startDate': start_date,
            'endDate': end_date,
            'date': date,
            'time': time,
            'total': total,
            'additionalFees': additional_fees,
            'hostId': host_id,
            'createdAt': datetime.utcnow().isoformat()
        }

        table.put_item(Item=item)

        return Response(
            status_code=200,
            body=json.dumps(item)
        )

    except Exception as e:
        logger.error(f"Error creating order: {str(e)}")
        return Response(
            status_code=500,
            body=json.dumps({
                "message": "Internal server error",
                "details": str(e)
            })
        )
