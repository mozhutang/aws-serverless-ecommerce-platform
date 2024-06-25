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
        order_id = event.path_parameters['orderId']
        body = event.json_body
        token = event.headers.get('Authorization')

        # Decode token to get user information
        user_info = cognito.get_user(AccessToken=token)
        user_sub = next(attr['Value'] for attr in user_info['UserAttributes'] if attr['Name'] == 'sub')

        response = table.get_item(Key={'orderId': order_id})
        item = response.get('Item')

        if not item:
            return Response(
                status_code=400,
                body=json.dumps({"message": "Invalid order ID", "code": 400, "details": "Order ID provided is not valid."})
            )

        # Ensure the user has access to the order (either userId or hostId matches)
        if item['userId'] != user_sub and item['hostId'] != user_sub:
            return Response(
                status_code=403,
                body=json.dumps({"message": "User is not authorized to update this order"})
            )

        # Update the order with provided data
        update_expression = "set "
        expression_attribute_values = {}
        for key, value in body.items():
            update_expression += f"{key} = :{key}, "
            expression_attribute_values[f":{key}"] = value

        update_expression = update_expression.rstrip(", ")

        table.update_item(
            Key={'orderId': order_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )

        return Response(
            status_code=200,
            body=json.dumps({"message": "Order updated successfully"})
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
