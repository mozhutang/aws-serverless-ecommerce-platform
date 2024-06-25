import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools.logging import Logger
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent
from aws_lambda_powertools.utilities.data_classes.api_gateway_proxy import Response

logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
cognito = boto3.client('cognito-idp')
table = dynamodb.Table(os.environ['TABLE_NAME'])

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event: APIGatewayProxyEvent, context):
    try:
        query_params = event.query_string_parameters or {}
        user_id = query_params.get('userId')
        listing_id = query_params.get('listingId')
        token = event.headers.get('Authorization')

        # Decode token to get user information
        user_info = cognito.get_user(AccessToken=token)
        user_sub = next(attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'sub')

        # Ensure the user has access to the orders
        if user_id and user_id != user_sub:
            return Response(
                status_code=403,
                body=json.dumps({"message": "User is not authorized to access these orders"})
            )

        if listing_id:
            response = table.query(
                IndexName='listingId-index',
                KeyConditionExpression=Key('listingId').eq(listing_id)
            )
            orders = response.get('Items', [])
            # Ensure the host has access to the orders
            if orders and orders[0]['hostId'] != user_sub:
                return Response(
                    status_code=403,
                    body=json.dumps({"message": "User is not authorized to access these orders"})
                )
        else:
            response = table.query(
                IndexName='userId-index',
                KeyConditionExpression=Key('userId').eq(user_sub)
            )
            orders = response.get('Items', [])

        return Response(
            status_code=200,
            body=json.dumps(orders)
        )

    except cognito.exceptions.NotAuthorizedException as e:
        logger.error(e)
        return Response(
            status_code=401,
            body=json.dumps({"message": "Unauthorized"})
        )
    except Exception as e:
        logger.error(e)
        return Response(
            status_code=500,
            body=json.dumps({"message": "Internal server error", "error": str(e)})
        )
