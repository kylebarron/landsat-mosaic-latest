from landsat_mosaic_latest.update_mosaic import main


def lambda_handler(event, context):
    # Extract SNS body
    sns_body = event['Records'][0]['Sns']

    try:
        main(sns_body)
        return {'message': 'Success', 'event': event, 'statusCode': 200}
    except Exception as e:
        return {
            'message': 'Failed',
            'event': event,
            'exception': e.args,
            'statusCode': 500}
