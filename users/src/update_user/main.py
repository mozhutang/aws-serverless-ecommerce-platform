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
    user_id_to_update = api_event.path_parameters['userId']
    token = api_event.headers.get('Authorization', '')

    try:
        # Verify token and get the user info
        response = cognito.get_user(
            AccessToken=token
        )
        
        user_id_from_token = response['Username']

        if user_id_from_token != user_id_to_update:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'You can only update your own account',
                    'code': 400,
                    'details': 'User ID in token does not match the provided user ID'
                })
            }

        body = json.loads(event['body'])
        update_expression = "SET "
        expression_attribute_values = {}

        allowed_fields = {
            'financeInformation.paymentMethod': 'paymentMethod',
            'financeInformation.payoutInformation': 'payoutInformation',
            'financeInformation.taxInformation': 'taxInformation'
        }

        for field, subfield in allowed_fields.items():
            if subfield in body.get('financeInformation', {}):
                for key, value in body['financeInformation'][subfield].items():
                    update_expression += f"{field}.{key} = :{subfield}_{key}, "
                    expression_attribute_values[f":{subfield}_{key}"] = value

        if not expression_attribute_values:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'No valid fields to update',
                    'code': 400,
                    'details': 'Only financeInformation.paymentMethod, financeInformation.payoutInformation, and financeInformation.taxInformation are allowed'
                })
            }

        update_expression = update_expression.rstrip(', ')

        users_table.update_item(
            Key={'userId': user_id_to_update},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        response = users_table.get_item(Key={'userId': user_id_to_update})
        updated_user_info = response.get('Item', {})

        return {
            'statusCode': 200,
            'body': json.dumps(updated_user_info)
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
