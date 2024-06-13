import json
import os
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent

logger = Logger()
tracer = Tracer()

dynamodb = boto3.resource('dynamodb')
cognito = boto3.client("cognito-idp")
users_table = dynamodb.Table(os.environ['TABLE_NAME'])

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    api_event = APIGatewayProxyEvent(event)
    user_id_to_get = api_event.path_parameters['userId']
    token = api_event.headers.get('Authorization', '')

    try:
        # Verify token and get the user info
        response = cognito.get_user(
            AccessToken=token
        )
        
        user_id_from_token = response['Username']

        # Get user information from DynamoDB
        response = users_table.get_item(Key={'userId': user_id_to_get})
        user_info = response.get('Item', None)

        if not user_info:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Invalid user ID',
                    'code': 400,
                    'details': 'User ID provided is not valid.'
                })
            }

        if user_id_from_token == user_id_to_get:
            # Return full user information
            return {
                'statusCode': 200,
                'body': json.dumps(user_info)
            }
        
        # Return limited user information
        limited_user_info = {
            'userId': user_info['userId'],
            'email': user_info['email'],
            'profile': user_info.get('profile', {}),
            'userType': user_info['userType']
        }
        return {
            'statusCode': 200,
            'body': json.dumps(limited_user_info)
        }
    
    except cognito.exceptions.NotAuthorizedException as error:
        logger.error(error)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid token',
                'code': 400,
                'details': str(error)
            })
        }
    except Exception as error:
        logger.error(error)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'code': 500,
                'details': str(error)
            })
        }
