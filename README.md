# DelaySay

A Slack app that schedules messages

Note: The directions below explain how to create the Slack app using the code in this repo. Please keep in mind they are only rough directions that may be incomplete or out of date.


## Prerequisites

- Slack workspace with admin access

- AWS account

- a domain with DNS hosted in AWS Route 53

- aws-cli:
    - <https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html>

- sam-cli:
    - <https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html>

- Docker:
    - For Ubuntu 20.04:
      - <https://www.omgubuntu.co.uk/how-to-install-docker-on-ubuntu-20-04/amp>
      - <https://docs.docker.com/engine/install/linux-postinstall/>

- Python 3.10

- Packages

      for requirements in code-*/requirements.txt; do
        python3.10 -m pip install -r $requirements
      done


## How to deploy the CloudFormation stack

In your local repo directory, create a subdirectory `secrets/` with three new files:
- `load-delaysay-environment-variables-general`
- `load-delaysay-environment-variables-prod`
- `load-delaysay-environment-variables-dev`

In `secrets/load-delaysay-environment-variables-general`, set these environment variables to match your preferences:
    
    #!/bin/bash
    export AWS_PROFILE=myAWSprofile   # the .aws/config profile you want to use
    export DELAYSAY_REGION=us-east-1
    export DELAYSAY_DOMAIN_NAME=See_Step_0
    export DELAYSAY_CONTACT_PAGE=See_Step_0
    export DELAYSAY_SUPPORT_EMAIL=See_Step_0
    export DELAYSAY_BILLING_PORTAL_FAIL_URL=See_Step_0
    export DELAYSAY_INSTALL_SUCCESS_URL=See_Step_0
    export DELAYSAY_INSTALL_CANCEL_URL=See_Step_0
    export DELAYSAY_INSTALL_FAIL_URL=See_Step_0
    export DELAYSAY_STRIPE_CHECKOUT_SIGNING_SECRET=delaysay/stripe/webhook-checkout-signing-secret
    export DELAYSAY_STRIPE_API_KEY=delaysay/stripe/webhook-api-key
    export DELAYSAY_STRIPE_TESTING_API_KEY=delaysay/stripe/webhook-testing-api-key
    export DELAYSAY_ENV_VARS_1_LOADED=yep

In `secrets/load-delaysay-environment-variables-prod` and `secrets/load-delaysay-environment-variables-dev`, set these environment variables, changing them appropriately to match your production and development environments:

    #!/bin/bash
    export DELAYSAY_SLASH_COMMAND=/delay
    export DELAYSAY_SLASH_COMMAND_LINKS_DOMAIN=See_Step_0
    export DELAYSAY_SUBSCRIBE_URL=See_Step_0
    export DELAYSAY_TABLE_NAME=DelaySay
    export DELAYSAY_STACK_NAME=delaysay
    export DELAYSAY_DEPLOY_BUCKET=delaysay-deploy-$RANDOM$RANDOM
    export DELAYSAY_API_DOMAIN_NAME=See_Step_0
    export DELAYSAY_SLACK_OAUTH_URL='See_Step_3'
    export DELAYSAY_SLACK_SIGNING_SECRET=delaysay/slack/signing-secret
    export DELAYSAY_STRIPE_TESTING_CHECKOUT_SIGNING_SECRET=delaysay/stripe/webhook-testing-checkout-signing-secret
    export DELAYSAY_SLACK_CLIENT_ID=delaysay/slack/client-id
    export DELAYSAY_SLACK_CLIENT_SECRET=delaysay/slack/client-secret
    export DELAYSAY_KMS_MASTER_KEY_ARN=See_Step_4
    export DELAYSAY_KMS_MASTER_KEY_ALIAS=delaysay/prod-key
    export DELAYSAY_ENV_VARS_2_LOADED=yep

Make the files executable:

    chmod +x secrets/load-delaysay-environment-variables-general secrets/load-delaysay-environment-variables-prod secrets/load-delaysay-environment-variables-dev

To deploy to your development environment:

    ./deploy-delaysay-sam dev

After you've tested your development environment, to deploy to your production environment:

    ./deploy-delaysay-sam prod


## STEP 0: Set up your website/domain

TBD: Register a domain, find the DNS, etc.

Set these environment variables:

$DELAYSAY_DOMAIN_NAME:
- your website's domain
- example.com
- DON'T include "http://" or "https://", because template.yaml adds those in for certain environment variables, but they're not used for Route 53.
- Also, DON'T end the URL with a slash.

$DELAYSAY_API_DOMAIN_NAME
- a path at your website where your whole app will be hosted!
- api.example.com
- So the Route 53 configuration works, DON'T include "http://" or "https://" and also DON'T end the URL with a slash.

$DELAYSAY_SUBSCRIBE_URL:
- a page on your website that redirects to a Stripe subscription creation page
- example.com/subscribe
- You can use HTTP or HTTPS.
- DON'T use an ending slash, because the slash command app.py will add in a slash and query string parameter(s) (like the team ID) later on.

$DELAYSAY_CONTACT_PAGE:
- the contact page on your website
- example.com/contact/
- You can use HTTP or HTTPS; you can also use an ending slash or not.

$DELAYSAY_SUPPORT_EMAIL:
- an email address
- team@example.com
- Preferably set up and use an email at your domain, but you don't have to.

$DELAYSAY_BILLING_PORTAL_FAIL_URL:
- a page on your website that says the provided token is invalid & it can't redirect to the team's Stripe customer portal
- https://example.com/invalid-billing-url/
- You can also use an ending slash or not. I think you can also use HTTP or HTTPS.

$DELAYSAY_INSTALL_SUCCESS_URL:
- a page on your website that congratulates the user on installing/authorizing the Slack app
- https://example.com/add-success/

$DELAYSAY_INSTALL_CANCEL_URL:
- a page on your website that tells the user they canceled installation/authorization of the Slack app
- https://example.com/add-canceled/

$DELAYSAY_INSTALL_FAIL_URL:
- a page on your website that says Slack app installation/authorization failed
- https://example.com/add-failed/

$DELAYSAY_SLASH_COMMAND_LINKS_DOMAIN:
- a base URL that the slash command can send users to (for API events like /add/?team=abc or /billing/?token=abc)
- https://api.example.com
- DON'T end it with a slash, because the slash command app.py will add in a slash and paths later on.
- If you're using your $DELAYSAY_API_DOMAIN_NAME, you *must* use HTTPS (NOT just api.example.com and NOT http://api.example.com).
- If you're using a link that redirects to your API (again, using HTTPS), then your link can be HTTP or HTTPS. If you do this, be sure to pass along query string parameters to your API though!


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

Configure the slash command:

- Under **"Features"**, click **"Slash Commands"**
- Click **[Create New Command]**
- Fill out the form:
    - Command: *[Use the value in $DELAYSAY_SLASH_COMMAND]*
    - Request URL: *[Use the $endpoint_url value from earlier with "https://" at the beginning and "/slash-command" (the event path from your slash command function in template.yaml) at the end. So if you have a custom domain, it will be something like api.example.com/slash-command]*
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
- "IAM users and roles that can use the CMK in cryptographic operations": *[Select the roles from DelaySaySecondResponderFunction and DelaySayUserAuthorizationFunction]*
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

(Replace "/delay" with whatever you decided to fill $DELAYSAY_SLASH_COMMAND with.)


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
- Click **"Add product"**
    - Product name: **"DelaySay Slack app"**
    - Leave the unit label and statement descriptor blank (default)
    - Price information:
        - Pricing model: **"Standard pricing"**
        - Price: Choose a price (charged every month) and select **"Recurring"** (Be sure to check the currency)
        - Billing period: **"Monthly"**
        - Leave **"Usage is metered"** unchecked
        - Price description: recurring-1month-earlyadopter
        - Don't add a free trial
    - To add a different billing plan or frequency, choose **"Add another price"**
- Click the three dots and **"Get Checkout code snippet"**
    - Update the success and cancel URLs as needed
    - Paste the code snippet into your website
- On the side bar, toggle on **"View test data"** and follow the steps again for a test product and test pricing plan (Add " [TEST]" to the end of the product name and "test-" to the beginning of the plan description if you'd like.)

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
