# DelaySay

A Slack app that schedules messages

Note: The directions below explain how to create the Slack app using the code in this repo. Please keep in mind they are only rough directions that may be incomplete or out of date.


## Prerequisites

- Slack workspace with admin access

- AWS account

- a domain with DNS hosted in AWS Route 53

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
    export DELAYSAY_API_DOMAIN_NAME=PleaseSeeTheSectionOnMovingTheAPIGateway
    export DELAYSAY_DOMAIN_NAME=PleaseSeeTheSectionOnMovingTheAPIGateway
    export DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET=delaysay/stripe/webhook-checkout-signing-secret
    export DELAYSAY_STRIPE_API_KEY=delaysay/stripe/webhook-api-key
    export DELAYSAY_STRIPE_TESTING_API_KEY=delaysay/stripe/webhook-testing-api-key
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
        "DelaySayApiDomain=$DELAYSAY_API_DOMAIN_NAME" \
        "DelaySayDomain=$DELAYSAY_DOMAIN_NAME" \
        "StripeCheckoutSigningSecretSsmName=$DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET" \
        "StripeApiKeySsmName=$DELAYSAY_STRIPE_API_KEY" \
        "StripeTestingApiKeySsmName=$DELAYSAY_STRIPE_TESTING_API_KEY" \
        "SlackSigningSecretSsmName=$DELAYSAY_SLACK_SIGNING_SECRET" \
        "SlackClientIdSsmName=$DELAYSAY_SLACK_CLIENT_ID" \
        "SlackClientSecretSsmName=$DELAYSAY_SLACK_CLIENT_SECRET" \
        "KmsMasterKeyArn=$DELAYSAY_KMS_MASTER_KEY_ARN"

Get the endpoint URL (It should be at your custom domain, as described in the step below about moving the API Gateway endpoint.)
TBD: Update the parameter name when it changes

    endpoint_url=$(aws cloudformation describe-stacks \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME" \
      --output text \
      --query 'Stacks[].Outputs[?OutputKey==`DelaySayApi`][OutputValue]')
    echo endpoint_url=$endpoint_url

Save this endpoint URL for configuring the Slack app and Stripe account below.

In your Lambda console, change the function's timeout to 5 minutes. (Just in case! That way Lambda doesn't silently time out and leave the user wondering what happened.)

In your IAM console, create a policy that allows the action "lambda:InvokeFunction" on your Lambda function's ARN. Attach it to the Lambda's IAM role.


## Move the API Gateway endpoint to a custom domain

Replace the value of $DELAYSAY_DOMAIN_NAME with your website's domain name (example.com).

For the API domain, choose a path at your website (api.example.com).

Validate the ACM Certificate by creating a DNS record in Route 53 (This must be done again if $DELAYSAY_API_DOMAIN_NAME ever changes.):

- Complete the steps below while you wait for CloudFormation to finish deploying the first time.
- In the AWS Certificate Manager console, expand the entry with your domain name. Its status should be "Pending validation." Find your domain again and expand it.
- Click "Create record in Route 53"
- Click "Create"

Replace the value of $DELAYSAY_API_DOMAIN_NAME with the domain name you chose.


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

Create a Stripe account at https://dashboard.stripe.com/register

Verify your email and activate your account.

Connect Stripe to Lambda:

- Under **"Developers"**, click **"Webhooks"**
- Click **"Add endpoint"**
- Paste the URL of your Stripe checkout Lambda's API Gateway endpoint. Check template.yaml if you're not sure of the path.
- For **"Events to send"**, select "checkout.session.completed"
- Save the signing secret in the SSM Parameter Store. Its parameter name should be the value of $DELAYSAY_STRIPE_API_KEY (but starting with a slash). It should be of type SecureString and encrypted with the KMS Key alias/aws/ssm.
- Toggle on **"View test data"**, then **"Reveal live key token"**, and store the key the same way, this time in $DELAYSAY_STRIPE_TESTING_API_KEY (still starting with a slash).
- Also add a hooks.slack.com endpoint??

Save the Stripe signing signature:

- Under **"Developers"**, click **"Webhooks"**
- Click **"Reveal live key token"**
- Save the key in the SSM Parameter Store. Its parameter name should be the value of $DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET (but starting with a slash). It should be of type SecureString and encrypted with the KMS Key alias/aws/ssm.

Create pricing plans:

- Click **"Products"**
- Click **"New"**
    - What kind of product? Recurring products
    - Product name: DelaySay Slack app
    - Leave the unit label and statement descriptor blank (default)
- Create the product and add a pricing plan:
    - Plan nickname: recurring-1month-earlyadopter
    - Leave the ID, pricing, currency, tiers, and trial period as their defaults
    - For a $5/month plan:
        - Price per unit: $5.00 per unit
        - Billing interval: Monthly
- Create the pricing plan and click **"Use with Checkout"**
    - Update the success and cancel URLs as needed
    - Make note of the example script for creating a checkout button
- On the side bar, toggle on **"View test data"** and follow the steps again for a test product and test pricing plan (Add " [TEST]" to the end of the product name and "test-" to the beginning of the plan nickname if you'd like.)

If you want to add team members:

- Click **"Settings"**
- Under **"Team and Security"**, click **"Team members"**
- Click **"New user"** and input the team member's information


## Create customer master key (CMK)

In your KMS console, create a new key:

- For the key type, select **"Symmetric"**
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

Delete the Stripe account (the business, not the user/profile)
- Log into your Stripe account
- Click **"Settings"**
- Under **"Your Business"**, click **"Account information"
- Scroll down and click **"Close account"**


## Credits

Team members:

- Kira Hammond: Lead developer

- Eric Hammond: Project manager & technical advisor

- Nicholas Hammond: Slack configuration & moral support

Code copied liberally from these excellent resources:

- Hello World code generated by `sam init --runtime python3.7`

- https://github.com/awslabs/serverless-application-model/blob/master/examples/apps/slack-echo-command-python/


## Other helpful resources

https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-getting-started-hello-world.html
