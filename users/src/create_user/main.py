import json
import os
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger

logger = Logger()
tracer = Tracer()

cognito = boto3.client("cognito-idp")
user_pool_id = os.environ['USER_POOL_ID']

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    try:
        body = json.loads(event['body'])
        email = body['email']
        user_type = body['userType']
        password = body['password']

        # Validate userType
        if user_type not in ['host', 'guest']:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Invalid user type. Must be either "host" or "guest".',
                    'code': 400,
                    'details': f'Provided userType: {user_type}'
                })
            }

        # Create user in Cognito
        response = cognito.admin_create_user(
            UserPoolId=user_pool_id,
            Username=email,
            UserAttributes=[
                {'Name': 'email', 'Value': email},
                {'Name': 'email_verified', 'Value': 'true'}
            ],
            MessageAction='SUPPRESS'
        )

        user_id = response['User']['Username']

        # Set user password
        cognito.admin_set_user_password(
            UserPoolId=user_pool_id,
            Username=user_id,
            Password=password,
            Permanent=True
        )
        
        # Add user to the specified group
        cognito.admin_add_user_to_group(
            UserPoolId=user_pool_id,
            Username=user_id,
            GroupName=user_type
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'userId': user_id,
                'email': email,
                'userType': user_type
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
