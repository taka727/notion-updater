import json

# import requests


def lambda_handler(event, context):
    from main import main
    main()
    return {
        "statusCode": 200,
        "body": "Notion update complete"
    }
