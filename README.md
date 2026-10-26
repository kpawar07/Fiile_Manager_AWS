# Smart Cloud File Manager

Starter mini-project: React + Vite frontend and a Python AWS Lambda backend.

## Features
- Upload files to a private S3 bucket using short-lived presigned URLs
- List files from DynamoDB metadata
- Download using short-lived presigned URLs
- Delete from the active list (S3 versioning retains historical versions)
- View versions and restore an earlier S3 version
- File size and upload date display

## AWS resources to create
1. S3 bucket with Block Public Access ON and Versioning ENABLED.
2. S3 CORS allowing `http://localhost:5173` with PUT, GET, HEAD.
3. DynamoDB table `SmartFileMetadata`, partition key `fileId` (String).
4. Lambda execution role with `AWSLambdaBasicExecutionRole` and narrowly scoped S3/DynamoDB permissions.
5. Python 3.12 Lambda function using `backend/lambda_function.py` as `lambda_function.handler`.
6. Environment variables on Lambda:
   - `BUCKET_NAME` = your bucket name
   - `TABLE_NAME` = `SmartFileMetadata`
   - `ALLOWED_ORIGIN` = `http://localhost:5173`
   AWS_REGION is supplied by Lambda.
7. API Gateway HTTP API with Lambda proxy integration, route `$default` (all paths/methods), and CORS:
   - Allowed origin: `http://localhost:5173`
   - Allowed methods: GET, POST, DELETE, OPTIONS
   - Allowed headers: Content-Type
8. Copy the API base URL into `frontend/.env` as `VITE_API_BASE_URL`.

## Deploy Lambda
Create a Lambda function with Python 3.12, upload `backend/lambda_function.py` as a ZIP or paste its content into the console editor, set handler to `lambda_function.handler`, set the execution role, and add the environment variables above. Boto3 is available in the standard Python Lambda runtime.

## Run the frontend
Install Node.js LTS, then from the `frontend` directory:
```bash
npm install
cp .env.example .env
# Edit .env and set your API URL
npm run dev
```
Open the local URL Vite prints, normally `http://localhost:5173`.

## Test checklist
- Upload a small PDF or image
- Confirm it appears in the list
- Download it
- Delete it and confirm it disappears from the active list
- Upload multiple versions of the same object key if testing version history directly in S3; the starter app creates a unique key per upload, so version history will usually show one version per file until you add a replace-file feature
- Test restore on a file with at least two S3 versions

## Important limitations and security
This is an educational demo, not production-ready. The API currently has no user authentication; do not put sensitive files in it or expose it publicly. Add Amazon Cognito/API authorization and user-specific ownership checks before real use. Restrict API Gateway access where possible. The demo limits uploads to 10 MB and scans the DynamoDB table, which is acceptable only for small demonstrations.

The frontend requests a presigned PUT URL then uploads directly to S3. The Lambda verifies the object exists before writing metadata. Presigned URLs are bearer tokens: do not log or share them. Review current AWS pricing and billing alerts before deployment, and delete resources after the project demo.
