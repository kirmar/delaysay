# DelaySay

A Slack app that schedules messages

Note: The directions below explain how to create the Slack app using the code in this repo. Please keep in mind they are only rough directions that may be incomplete or out of date.


## Prerequisites

- Slack workspace with admin access

- AWS account

- a domain with DNS hosted in AWS Route 53

- aws-cli: <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html>

- sam-cli: <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html>

- Docker:
    For Ubuntu 20.04:
    <https://www.omgubuntu.co.uk/how-to-install-docker-on-ubuntu-20-04/amp>
    <https://docs.docker.com/engine/install/linux-postinstall/>

- Python 3.8

- Packages

    for requirements in code-*/requirements.txt; do
      python3.8 -m pip install -r $requirements
    done


## How to deploy the CloudFormation stack

Set environment variables to match your preferences:
    
    export AWS_PROFILE=myAWSprofile   # the .aws/config profile you want to use
    export DELAYSAY_REGION=us-east-1
    export DELAYSAY_DOMAIN_NAME=example.com     # your website's domain
    export DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET=delaysay/stripe/webhook-checkout-signing-secret
    export DELAYSAY_STRIPE_TESTING_CHECKOUT_SIGNING_SECRET=delaysay/stripe/webhook-testing-checkout-signing-secret
    export DELAYSAY_STRIPE_API_KEY=delaysay/stripe/webhook-api-key
    export DELAYSAY_STRIPE_TESTING_API_KEY=delaysay/stripe/webhook-testing-api-key
    
    # Change these depending on whether you're deploying to the
    # production or development environment:
    export DELAYSAY_TABLE_NAME=DelaySay
    export DELAYSAY_STACK_NAME=delaysay
    export DELAYSAY_DEPLOY_BUCKET=delaysay-deploy-$RANDOM$RANDOM
    export DELAYSAY_API_DOMAIN_NAME=api.example.com    # a path at your website
    export DELAYSAY_SLACK_OAUTH_URL='See_Step_3'
    export DELAYSAY_SLACK_SIGNING_SECRET=delaysay/slack/signing-secret
    export DELAYSAY_SLACK_CLIENT_ID=delaysay/slack/client-id
    export DELAYSAY_SLACK_CLIENT_SECRET=delaysay/slack/client-secret
    export DELAYSAY_KMS_MASTER_KEY_ARN=See_Step_4
    export DELAYSAY_KMS_MASTER_KEY_ALIAS=delaysay/prod-key

Build and package SAM app:

    sam build --use-container
    sam package \
      --output-template-file packaged.yaml \
      --s3-bucket "$DELAYSAY_DEPLOY_BUCKET"

Deploy the SAM app:

    sam deploy \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME" \
      --template-file packaged.yaml \
      --capabilities CAPABILITY_IAM \
      --parameter-overrides \
        "DelaySayTableName=$DELAYSAY_TABLE_NAME" \
        "DelaySayApiDomain=$DELAYSAY_API_DOMAIN_NAME" \
        "DelaySayDomain=$DELAYSAY_DOMAIN_NAME" \
        "SlackOAuthUrl=$DELAYSAY_SLACK_OAUTH_URL" \
        "StripeCheckoutSigningSecretSsmName=$DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET" \
        "StripeTestingCheckoutSigningSecretSsmName=$DELAYSAY_STRIPE_TESTING_CHECKOUT_SIGNING_SECRET" \
        "StripeApiKeySsmName=$DELAYSAY_STRIPE_API_KEY" \
        "StripeTestingApiKeySsmName=$DELAYSAY_STRIPE_TESTING_API_KEY" \
        "SlackSigningSecretSsmName=$DELAYSAY_SLACK_SIGNING_SECRET" \
        "SlackClientIdSsmName=$DELAYSAY_SLACK_CLIENT_ID" \
        "SlackClientSecretSsmName=$DELAYSAY_SLACK_CLIENT_SECRET" \
        "KmsMasterKeyArn=$DELAYSAY_KMS_MASTER_KEY_ARN"


## STEP 1: Create the Slack App

Create a new Slack app:

- Visit https://api.slack.com/apps
- Click **[Create New App]**

Set up the app's scopes:

- Under **"Features"**, click **"OAuth & Permissions"**
- Under **"Scopes"**,
  - Bot Token Scopes:
    - chat:write
    - commands
  - User Token Scopes:
    - chat:write
    - users:read

TBD: Other configuration

Save secrets in AWS:

- Under **"Settings"**, click **"Basic Information"**
- Scroll down to **"App Credentials"**
- Save the Slack signing secret as a parameter in the SSM Parameter Store:
    - Name: *[Paste the value in $DELAYSAY_SLACK_SIGNING_SECRET, but be sure to add a starting slash! Otherwise, it'll raise an error like "Parameter name must be a fully qualified name" and prevent you from creating the parameter.]*
    - Tier: **`Standard`**
    - Type: **`SecureString`**
    - KMS Key ID: **`alias/aws/ssm`**
- Do the same for the client id:
    - Name: *[value in $DELAYSAY_SLACK_CLIENT_ID with a starting slash]*
- Do the same for the client secret
    - Name: *[value in $DELAYSAY_SLACK_CLIENT_SECRET with a starting slash]*


## STEP 2: Deploy the CloudFormation stack in AWS

Clone the delaysay GitHub repository

    git clone git@github.com:kirmar/delaysay.git
    cd delaysay


Deploy the CloudFormation stack as described above, keeping in mind:

- Some of the environment variables' values will change in the indicated step. But the first time you deploy, leave them as they are.

- After exporting the environment variables and before running the `sam` commands, create the S3 bucket for SAM deployments:

      aws s3 mb \
        --region "$DELAYSAY_REGION" \
        s3://$DELAYSAY_DEPLOY_BUCKET

- When you run `sam deploy` the first time, it will eventually pause and wait for you. You must complete Step 2B for it to finish.


Get the endpoint URL (It should be a path at your custom API domain, as described in the step below about moving the API Gateway endpoint.)
TBD: Update the parameter name when it changes

    endpoint_url=$(aws cloudformation describe-stacks \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME" \
      --output text \
      --query 'Stacks[].Outputs[?OutputKey==`DelaySayApi`][OutputValue]')
    echo endpoint_url=$endpoint_url

Save this endpoint URL for configuring the Slack app and Stripe account later on.

In your IAM console, create a policy that allows the action "lambda:InvokeFunction" on your slash command Lambda function's ARN. Attach it to the slash command Lambda's IAM role. (TBD: Add this IAM policy to template.yaml instead of having the developer do it manually)


## STEP 2B: Validate the DelaySay API's ACM Certificate

Complete this step while you wait for CloudFormation to finish deploying the first time. It must be done again if $DELAYSAY_API_DOMAIN_NAME ever changes.

Validate the ACM Certificate by creating a DNS record in Route 53:

- In the AWS Certificate Manager console, expand the entry with your domain name. Its status should be "Pending validation." Find your domain again and expand it.
- Click "Create record in Route 53"
- Click "Create"

It'll take a while for the validation to finish and the CloudFormation stack to complete, but that's all you need to do!


## STEP 3: Finish configuring the Slack app
(Connect the Slack app configuration to the AWS API endpoints
& install the Slack app on your workspace.)

Configure the `/delay` Slack command:

- Under **"Features"**, click **"Slash Commands"**
- Click **[Create New Command]**
- Fill out the form:
    - Command: **`/delay`**
    - Request URL: *[Use $endpoint_url value from earlier with "https://" at the beginning and "/slash-command" (the event path from your slash command function in template.yaml) at the end. So if you have a custom domain, it will be something like api.example.com/slash-command]*
    - Short Description: **`Send [message] at [time] on current channel`**
    - Usage Hint: **`[time] say [message]`**
    - Check: **"Escape channels, users, and links sent to your app"**
- Click **[Save]**

Configure the redirect URL:

- Under **"Features"**, click **"OAuth & Permissions"**
- Under **"Redirect URLs"**, click **[Add New Redirect URL]**
- Use the $endpoint_url again with "https://" at the beginning, but this time ending with "/user-authorization" (or whatever the event path from your user auth function in template.yaml)
- Be sure to click **[Save URLs]**

Install the app on your workspace:

- Under **"Settings"**, click **"Install App"**
- If you're not an admin for your development workspace, click **[Request to Install]**
- After the installation is approved, click **[Install to Workspace]**

Save the installation URL:

- Under **"Settings"**, click **"Manage Distribution"**
- Copy the **"Shareable URL"** to $DELAYSAY_SLACK_OAUTH_URL, keeping single quotes around the URL because it has ampersands in it.


## STEP 4: Create the custom master key (CMK)
(This CMK is used to encrypt Slack user tokens in the DynamoDB table.)

In your KMS console, create a new key:

- Key type: **`Symmetric`**
- Key material origin: **`KMS`**
- Alias: *[Paste the value of $DELAYSAY_KMS_MASTER_KEY_ALIAS]*
- Key administrators: **`admin`**
- Check: **"Allow key administrators to delete this key."**
- "IAM users and roles that can use the CMK in cryptographic operations": *[Select the roles from DelaySayFunction and DelaySayUserAuthorizationFunction]*
- Finish.

Click the alias and copy the ARN to $DELAYSAY_KMS_MASTER_KEY_ARN.


## STEP 5: Deploy the app again now that everything has been filled out

Follow the deployment instructions again!

All the environment variables that had placeholders earlier are now filled out.


## STEP 6: Authorize the app to post messages using your identity
(Each individual user must do this.)

Visit your $DELAYSAY_SLACK_OAUTH_URL

Or! To test your workflow, visit https://{$DELAYSAY_API_DOMAIN_NAME}/add/ or whatever the event path for your install redirect Lambda function! The full URL should be something like https://api.example.com/add/


## YAY!

The app now works in the Slack workspace you installed it to! Test it out by sending the message `/delay 15 sec say Hello world!`


## STEP 7: Activate public distribution

Under **"Settings"**:

- Click **"Manage Distribution"**
- Click **"Activate Public Distribution"**

Add **"Embeddable Slack Button"** to your app's website, but replace the URL with https://{$DELAYSAY_API_DOMAIN_NAME}/add/ (or whatever the event path for your install redirect Lambda function).

Now anyone can install the app on their Slack workspace!


## STEP 8: Set up payment

Create a Stripe account at https://dashboard.stripe.com/register

Verify your email and activate your account.

Connect Stripe to Lambda:

- Under **"Developers"**, click **"Webhooks"**
- Toggle off **"Viewing test data"** (Make sure you're viewing the live data.)
- Click **"Add endpoint"**
- Like in the Slack app configuration, use the $endpoint_url again with "https://" at the beginning, but this time ending with "/stripe-checkout-webhook" (or whatever the event path from your Stripe checkout function in template.yaml)
- For **"Events to send"**, select "checkout.session.completed"
- **"Reveal live key token"**
- Save the signing secret in the SSM Parameter Store.
    - Name: *[the value of $DELAYSAY_STRIPE_API_KEY, but add a starting slash!]*
    - Tier: **`Standard`**
    - Type: **`SecureString`**
    - KMS Key ID: **`alias/aws/ssm`**
- Toggle on **"View test data"**, then **"Reveal test key token"**, and store the key the same way, this time in $DELAYSAY_STRIPE_TESTING_API_KEY (still starting with a slash).
- TBD: Also add a hooks.slack.com endpoint?

Save the Stripe signing signature:

- Under **"Developers"**, click **"Webhooks"**
- Toggle off **"Viewing test data"** (Make sure you're viewing the live data.)
- **"Click to reveal"**
- Save the key in the SSM Parameter Store:
    - Name: *[the value of $DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET, but add a starting slash!]*
    - Tier: **`Standard`**
    - Type: **`SecureString`**
    - KMS Key ID: **`alias/aws/ssm`**
- Toggle on **"View test data"**, then **"Click to reveal"**, and store the testing key the same way, this time in $DELAYSAY_STRIPE_TESTING_CHECKOUT_SIGNING_SECRET (still starting with a slash).

Create pricing plans:

- Toggle off **"Viewing test data"** (Make sure you're viewing the live data.)
- Click **"Products"**
- Click **"New"**
    - What kind of product? **"Recurring products"**
    - Product name: **"DelaySay Slack app"**
    - Leave the unit label and statement descriptor blank (default)
- Create the product and add a pricing plan:
    - Plan nickname: recurring-1month-earlyadopter
    - Leave the ID, pricing, currency, tiers, and trial period as their defaults
    - For a $5/month plan:
        - Price per unit: **"$5.00 per unit"**
        - Billing interval: **"Monthly"**
- Create the pricing plan and click **"Use with Checkout"**
    - Update the success and cancel URLs as needed
    - Make note of the example script for creating a checkout button
- On the side bar, toggle on **"View test data"** and follow the steps again for a test product and test pricing plan (Add " [TEST]" to the end of the product name and "test-" to the beginning of the plan nickname if you'd like.)

If you want to add team members:

- Click **"Settings"**
- Under **"Team and Security"**, click **"Team members"**
- Click **"New user"** and input the team member's information


## STEP 9: Officially release the app!

Add the Slack app to the App Directory:

- Under **"Settings"**, click **"Submit to App Directory"**
- Follow the instructions Slack gives

(TBD: Provide more tips?)

After you submit to the app directory, update the installation process:
(can probably also do this while creating your submission request)

- Under **"Settings"**, click **"Basic Information"**
- Scroll down to **"Installing Your App"**
- Choose **"Install from App Directory"**
- Fill the **"Direct install URL"** with https://{$DELAYSAY_API_DOMAIN_NAME}/add/ (or whatever the event path for your install redirect Lambda function)


## Cleanup

WARNING! Only follow these instructions if you are done testing the
app and wish to delete all resources that were created.

Delete the AWS stack

    aws cloudformation delete-stack \
      --region "$DELAYSAY_REGION" \
      --stack-name "$DELAYSAY_STACK_NAME"

Delete the Slack app
- Under **"Settings"**, click **"Basic Information"**
- Scroll down and click **"Delete App"**

Delete the Stripe account (the business, not the user/profile)
- Log into your Stripe account
- Click **"Settings"**
- Under **"Your Business"**, click **"Account information"**
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
