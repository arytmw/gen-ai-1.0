import os
from dotenv import load_dotenv
import boto3


load_dotenv()
# Use your configured AWS credentials (for example, AWS_PROFILE).
region = os.getenv("AWS_REGION")
kb_id = os.getenv("BEDROCK_KB_ID")
model_arn = os.getenv("BEDROCK_MODEL_ARN")
question = input("Your question: ")

client = boto3.client("bedrock-agent-runtime", region_name=region)

# Bedrock retrieves relevant documents and asks the LLM to answer.
response = client.retrieve_and_generate(
    input={"text": question},
    retrieveAndGenerateConfiguration={
        "type": "KNOWLEDGE_BASE",
        "knowledgeBaseConfiguration": {
            "knowledgeBaseId": kb_id,
            "modelArn": model_arn,
        },
    },
)

print("\nAnswer:", response["output"]["text"])

# Print the S3 documents cited in the answer.
for citation in response.get("citations", []):
    for reference in citation.get("retrievedReferences", []):
        uri = reference.get("location", {}).get("s3Location", {}).get("uri")
        if uri:
            print("Source:", uri)
