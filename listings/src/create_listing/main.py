import json
import os
import uuid
import boto3
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

    # Validate JWT token and get user information
    try:
        user_info = cognito.get_user(AccessToken=token)
        user_sub = next(attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'sub')
        groups = cognito.list_groups_for_user(UserPoolId=user_info['UserPoolId'], Username=user_info['Username'])
        
        is_host = any(group['GroupName'] == 'host' for group in groups['Groups'])
        
        if not is_host:
            return Response(
                status_code=403,
                body=json.dumps({"message": "User is not authorized to create listings"})
            )
        
        body = json.loads(event['body'])
        listing_id = str(uuid.uuid4())

        item = {
            'listingId': listing_id,
            'Type': body['listingType'],
            'name': body['name'],
            'address': body['address'],
            'City': body['city'],
            'photoAddressList': body['photoAddressList'],
            'category': body['category'],
            'price': body['price'],
            'calendar': body['calendar'],
            'hostId': user_sub
        }

        table.put_item(Item=item)

        return Response(
            status_code=201,
            body=json.dumps({"message": "Listing created successfully", "listingId": listing_id})
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
