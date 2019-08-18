# DelaySay
A Slack app that schedules messages


## Installation

    git clone git@github.com:kirmar/delaysay.git
    cd delaysay/sam-app

    # Set environment variables
    deploy_bucket=delaysay-sam-deploy
    region=us-east-1
    
    # Build and package SAM app
    sam build
    sam package --output-template packaged.yaml --s3-bucket $deploy_bucket
    
    # Deploy the SAM app
    sam deploy --template-file packaged.yaml --region $region --capabilities CAPABILITY_IAM --stack-name aws-sam-getting-started
