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
def handler(event, context):
    token = event['headers'].get('Authorization')
    listing_id = event['pathParameters']['listingId']

    # Validate JWT token and get user information
    try:
        user_info = cognito.get_user(AccessToken=token)
        user_sub = next(attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'sub')
        
        response = table.get_item(Key={'listingId': listing_id})
        item = response.get('Item')

        if not item:
            return Response(
                status_code=400,
                body=json.dumps({"message": "Invalid listing ID", "code": 400, "details": "Listing ID provided is not valid."})
            )

        if item['hostId'] != user_sub:
            return Response(
                status_code=403,
                body=json.dumps({"message": "User is not authorized to delete this listing"})
            )

        table.delete_item(Key={'listingId': listing_id})

        return Response(
            status_code=200,
            body=json.dumps({"message": "Listing successfully deleted"})
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
