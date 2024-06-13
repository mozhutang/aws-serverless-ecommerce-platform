import datetime
import json
import os
from aws_lambda_powertools.tracing import Tracer
from aws_lambda_powertools.logging.logger import Logger
import boto3

ENVIRONMENT = os.environ["ENVIRONMENT"]
EVENT_BUS_NAME = os.environ["EVENT_BUS_NAME"]

eventbridge = boto3.client("events")
dynamodb = boto3.resource('dynamodb')
logger = Logger()
tracer = Tracer()

users_table = dynamodb.Table(os.environ['TABLE_NAME'])

@tracer.capture_method
def process_request(input_: dict) -> dict:
    """
    Transform the input request into an EventBridge event
    """

    output = {
        "Time": datetime.datetime.now(),
        "Source": "ecommerce.users",
        "Resources": [input_["userName"]],
        "DetailType": "UserCreated",
        "Detail": json.dumps({
            "userId": input_["userName"],
            "email": input_["request"]["userAttributes"]["email"]
        }),
        "EventBusName": EVENT_BUS_NAME
    }

    return output

@tracer.capture_method
def send_event(event: dict):
    """
    Send event to EventBridge
    """

    eventbridge.put_events(Entries=[event])

@tracer.capture_method
def save_user_to_dynamodb(user_id: str, email: str, user_role: str):
    """
    Save user information to DynamoDB
    """
    item = {
        'userId': user_id,
        'email': email,
        'profile': {
            'avatarPictureAddress': '',
            'about': '',
            'whereHaveBeen': [],
            'hobby': [],
            'languages': [],
            'favoriteSong': '',
            'location': '',
            'joinDate': datetime.datetime.now().date().isoformat(),
            'school': '',
            'work': '',
            'birthDecade': '',
            'funFactUselessSkill': ''
        },
        'personalInformation': {
            'legalName': '',
            'preferredFirstName': '',
            'phoneNumber': '',
            'address': '',
            'emergencyContact': {
                'name': '',
                'phone': '',
                'relationship': ''
            },
            'governmentID': ''
        },
        'financeInformation': {
            'paymentMethod': {
                'cardType': '',
                'lastFourDigits': '',
                'expiryDate': ''
            },
            'payoutInformation': {
                'bankName': '',
                'accountNumber': '',
                'routingNumber': ''
            },
            'creditsCoupons': {
                'totalCredits': 0,
                'activeCoupons': []
            },
            'taxInformation': {
                'taxID': '',
                'taxStatus': ''
            },
            'transactionHistory': []
        },
        'userType': user_role
    }
    users_table.put_item(Item=item)

@logger.inject_lambda_context
@tracer.capture_lambda_handler
def handler(event, _):
    """
    Lambda handler
    """

    logger.debug({
        "message": "Input event",
        "event": event
    })

    event["response"] = {
        "autoConfirmUser": False,
        "autoVerifyPhone": False,
        "autoVerifyEmail": False
    }

    if event["triggerSource"] not in ["PreSignUp_SignUp", "PreSignUp_AdminCreateUser"]:
        logger.warning({
            "message": "invalid triggerSource",
            "triggerSource": event["triggerSource"]
        })
        return event

    username = event["userName"]
    user_attributes = event["request"]["userAttributes"]
    email = user_attributes.get("email", "")
    user_role = event["request"]["clientMetadata"].get("role", "guest")

    save_user_to_dynamodb(username, email, user_role)

    eb_event = process_request(event)
    send_event(eb_event)

    return event
