# DelaySay

A Slack app that schedules messages


## Prerequisites

- Slack workspace with admin access

- AWS account

- aws-cli: <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html>

- sam-cli: <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html>

- Python 3.7


## Deploy AWS stack

Clone the delaysay GitHub repository

    git clone git@github.com:kirmar/delaysay.git
    cd delaysay

Set environment variables to match your preferences

    stack_name=delaysay
    deploy_bucket=$stack_name-deploy-$RANDOM$RANDOM
    region=us-east-1
    
Create the S3 bucket for SAM deployments

    aws s3 mb \
      --region "$region" \
      s3://$deploy_bucket

Build and package SAM app

    sam build
    sam package \
      --output-template packaged.yaml \
      --s3-bucket "$deploy_bucket"
    
Deploy the SAM app

    sam deploy \
      --region "$region" \
      --stack-name "$stack_name" \
      --template-file packaged.yaml \
      --capabilities CAPABILITY_IAM

Get the endpoint URL
TBD: Update the parameter name when it changes

    endpoint_url=$(aws cloudformation describe-stacks \
      --region "$region" \
      --stack-name "$stack_name" \
      --output text \
      --query 'Stacks[].Outputs[?OutputKey==`DelaySayApi`][OutputValue]')
    echo endpoint_url=$endpoint_url

Save this endpoint URL for configuring the Slack App below.

Test

    curl "$endpoint_url"

## Configure Slack App

TBD: Create app

TBD: Other configuration

Configure the `/delay` Slack command:

- Click *"Add Features and Functionality"*
- Click *"Slash Commands"*
- Click *[Create New Command]*
- Fill out the form:
    Command: *`/delay`*
    Request URL: _[Use $endpoint_url value above]_
    Short Description: *`Send [message] at [time] on current channel`*
    Usage Hint: *`[time] say [message]`*
    Escape channels, users, and links sent to your app: *[X]*
- Click *[Save]*


## Cleanup

WARNING! Only follow these instructions if you are done testing the
app and wish to delete all resources that were created.

Delete the AWS stack

    aws cloudformation delete-stack \
      --region "$region" \
      --stack-name "$stack_name"

Delete the Slack app

    TBD
