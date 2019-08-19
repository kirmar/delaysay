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

    export DELAYSAY_STACK_NAME=delaysay
    export DELAYSAY_DEPLOY_BUCKET=delaysay-deploy-$RANDOM$RANDOM
    export DELAYSAY_REGION=us-east-1
    
Create the S3 bucket for SAM deployments

    aws s3 mb \
      --region "$DELAYSAY_REGION" \
      s3://$DELAYSAY_DEPLOY_BUCKET

Build and package SAM app

    sam build
    sam package \
      --output-template packaged.yaml \
      --s3-bucket "$DELAYSAY_DEPLOY_BUCKET"
    
Deploy the SAM app

    sam deploy \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME" \
      --template-file packaged.yaml \
      --capabilities CAPABILITY_IAM

Get the endpoint URL
TBD: Update the parameter name when it changes

    endpoint_url=$(aws cloudformation describe-stacks \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME" \
      --output text \
      --query 'Stacks[].Outputs[?OutputKey==`DelaySayApi`][OutputValue]')
    echo endpoint_url=$endpoint_url

Save this endpoint URL for configuring the Slack App below.


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

## Install Slack App in workspace

TBD

Note: Each individual user who wants to use DelaySay may have to
authorize the app to post messages with their identity.


## Cleanup

WARNING! Only follow these instructions if you are done testing the
app and wish to delete all resources that were created.

Delete the AWS stack

    aws cloudformation delete-stack \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME"

Delete the Slack app

    TBD


## Credits

Team members:

- Kira Hammond: Lead developer

- Nicholas Hammond: Slack configuration & moral support

- Eric Hammond: Project manager & technical advisor

Code copied liberally from these excellent resources:

- Hello World code generated by `sam init --runtime python3.7`

- https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/


## Other helpful resources

https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-getting-started-hello-world.html
