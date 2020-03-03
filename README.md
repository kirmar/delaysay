# DelaySay

A Slack app that schedules messages

Note: These are only rough directions that may need a lot of updates.


## Prerequisites

- Slack workspace with admin access

- AWS account

- aws-cli: <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html>

- sam-cli: <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html>

- Python 3.7

- Packages

    for requirements in code-*/requirements.txt; do
      python3.7 -m pip install -r $requirements
    done

## Deploy AWS stack

Clone the delaysay GitHub repository

    git clone git@github.com:kirmar/delaysay.git
    cd delaysay

Set environment variables to match your preferences

    export DELAYSAY_STACK_NAME=delaysay
    export DELAYSAY_DEPLOY_BUCKET=delaysay-deploy-$RANDOM$RANDOM
    export DELAYSAY_REGION=us-east-1
    export DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET=delaysay/stripe/webhook-checkout-signing-secret
    export DELAYSAY_SLACK_SIGNING_SECRET=delaysay/slack/signing-secret
    export DELAYSAY_SLACK_CLIENT_ID=delaysay/slack/client-id
    export DELAYSAY_SLACK_CLIENT_SECRET=delaysay/slack/client-secret
    export DELAYSAY_KMS_MASTER_KEY_ARN=PleaseSeeTheSectionOnCreatingTheCMK
    export DELAYSAY_KMS_MASTER_KEY_ALIAS=delaysay/prod-key
    
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
      --capabilities CAPABILITY_IAM \
      --parameter-overrides \
        "StripeCheckoutSigningSecretSsmName=$DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET" \
        "SlackSigningSecretSsmName=$DELAYSAY_SLACK_SIGNING_SECRET" \
        "SlackClientIdSsmName=$DELAYSAY_SLACK_CLIENT_ID" \
        "SlackClientSecretSsmName=$DELAYSAY_SLACK_CLIENT_SECRET" \
        "KmsMasterKeyArn=$DELAYSAY_KMS_MASTER_KEY_ARN"

Get the endpoint URL
TBD: Update the parameter name when it changes

    endpoint_url=$(aws cloudformation describe-stacks \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME" \
      --output text \
      --query 'Stacks[].Outputs[?OutputKey==`DelaySayApi`][OutputValue]')
    echo endpoint_url=$endpoint_url

Save this endpoint URL for configuring the Slack App below.

In your Lambda console, change the function's timeout to 5 minutes. (Just in case! That way Lambda doesn't silently time out and leave the user wondering what happened.)

In your IAM console, create a policy that allows the action "lambda:InvokeFunction" on your Lambda function's ARN. Attach it to the Lambda's IAM role.


## Configure Slack App

TBD: Create app

TBD: Other configuration

Configure the `/delay` Slack command:

- Under **"Features"**, click **"Slash Commands"**
- Click **[Create New Command]**
- Fill out the form:
    Command: **`/delay`**
    Request URL: *[Use $endpoint_url value above]*
    Short Description: **`Send [message] at [time] on current channel`**
    Usage Hint: **`[time] say [message]`**
    Escape channels, users, and links sent to your app: **[X]**
- Click **[Save]**

Configure the redirect URL:

- Click **"OAuth & Permissions"**
- Under **"Redirect URLs"**, click **[Add New Redirect URL]**
- Paste the URL of your user authentication Lambda's API Gateway endpoint. Check template.yaml if you're not sure of the path.
- Click **[Save URLs]**

Navigate to **"App Credentials"** under **"Basic Information"** in your Slack app. Save the Slack signing secret, client id, and client secret in the SSM Parameter Store. Their parameter names should be the values of $DELAYSAY_SLACK_SIGNING_SECRET, $DELAYSAY_SLACK_CLIENT_ID, and $DELAYSAY_SLACK_CLIENT_SECRET.


## Install Slack App in workspace

TBD

Note: Each individual user who wants to use DelaySay may have to
authorize the app to post messages with their identity.


## Activate Public Distribution

Under **"Settings"**:

- Click **"Manage Distribution"**
- Click **"Activate Public Distribution"**

Copy the **"Shareable URL"** and **"Embeddable Slack Button"** to your app's website.


## Set up payment

TBD

Save the signing signature in the SSM Parameter Store. Its parameter name should be the value of $DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET.


## Create customer master key (CMK)

In your KMS console, create a new key.
- For the key type, select **"Symetric"**
- For the key material origin, select **"KMS"**
- For the alias, type in the value of $DELAYSAY_KMS_MASTER_KEY_ALIAS
- For the key administrators, select **"admin"**
- Allow key administrators to delete this key.
- For "IAM users and roles that can use the CMK in cryptographic operations," select the roles from DelaySayFunction and DelaySayUserAuthorizationFunction
- Finish.

Click the alias and copy the ARN to $DELAYSAY_KMS_MASTER_KEY_ARN.


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
