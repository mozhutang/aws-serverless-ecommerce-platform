import json
import os
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
from aws_lambda_powertools.utilities.data_classes import APIGatewayProxyEvent

logger = Logger()
tracer = Tracer()

cognito = boto3.client("cognito-idp")
user_pool_id = os.environ['USER_POOL_ID']

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    api_event = APIGatewayProxyEvent(event)
    user_id_to_deactivate = api_event.path_parameters['userId']
    token = api_event.headers.get('Authorization', '')

    try:
        # Verify token and get the user info
        response = cognito.get_user(
            AccessToken=token
        )
        
        user_id_from_token = response['Username']

        if user_id_from_token != user_id_to_deactivate:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'You can only deactivate your own account',
                    'code': 400,
                    'details': 'User ID in token does not match the provided user ID'
                })
            }
        
        # Deactivate the user
        cognito.admin_disable_user(
            UserPoolId=user_pool_id,
            Username=user_id_to_deactivate
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'User successfully deactivated'
            })
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
