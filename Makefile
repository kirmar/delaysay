
FUNCTION_NAME=DelaySayFunction
BUILD_TEMLATE=.aws-sam/build/template.yaml
PACKAGED=packaged.yaml

.PHONY: help validate build package deploy push logs-tail print-endpoint delete-stack-forever clean

help: ## Show help text
	@echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'
	@echo

validate:: ## Validate the SAM template
	sam validate

build:: ## SAM build
	sam build

package:: ## SAM package
	sam package \
	  --output-template $(PACKAGED) \
	  --s3-bucket "$(DELAYSAY_DEPLOY_BUCKET)"

deploy:: $(PACKAGED) ## Deploy stack $stack_name to $region
	sam deploy \
	  --region "$(DELAYSAY_REGION)" \
	  --stack-name "$(DELAYSAY_STACK_NAME)" \
	  --template-file $(PACKAGED) \
	  --capabilities CAPABILITY_IAM

push:: build package deploy ## build, package, deploy

logs-tail:: ## Tail the logs from the AWS Lambda function in stack $stack_name
	sam logs \
	  --region "$(DELAYSAY_REGION)" \
	  --stack-name "$(DELAYSAY_STACK_NAME)" \
	  --name $(FUNCTION_NAME) \
	  --tail

print-endpoint:: ## Display the API endpoint from the running stack $stack_name
	aws cloudformation describe-stacks \
	  --region "$(DELAYSAY_REGION)" \
	  --stack-name "$(DELAYSAY_STACK_NAME)" \
	  --output text \
	  --query 'Stacks[].Outputs[?OutputKey==`DelaySayApi`][OutputValue]'

delete-stack-forever:: # Delete stack $stack_name in $region with no prompting
	aws cloudformation delete-stack \
	  --region "$(DELAYSAY_REGION)" \
	  --stack-name "$(DELAYSAY_STACK_NAME)"

clean:: ## Clean up local directory
