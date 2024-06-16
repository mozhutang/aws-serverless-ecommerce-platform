import json
import os
import boto3
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger

logger = Logger()
tracer = Tracer()

cognito = boto3.client("cognito-idp")
user_pool_id = os.environ['USER_POOL_ID']
client_id = os.environ['CLIENT_ID']

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    try:
        body = json.loads(event['body'])
        email = body['email']
        password = body['password']

        # Initiate auth to get JWT token
        response = cognito.admin_initiate_auth(
            UserPoolId=user_pool_id,
            ClientId=client_id,
            AuthFlow="ADMIN_NO_SRP_AUTH",
            AuthParameters={
                "USERNAME": email,
                "PASSWORD": password
            }
        )
        
        token = response["AuthenticationResult"]["IdToken"]

        return {
            'statusCode': 200,
            'body': json.dumps({
                'token': token
            })
        }
    except cognito.exceptions.NotAuthorizedException as error:
        logger.error(error)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Invalid email or password',
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
